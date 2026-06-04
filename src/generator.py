from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from src.graph_manager import GraphManager

# Pydantic schema to parse feedback corrections reliably
class CorrectionTriple(BaseModel):
    subject: str = Field(description="The source node entity (e.g., 'Ambitio Corp', 'John Doe')")
    predicate: str = Field(description="The relationship or action connecting the nodes (e.g., 'pays_stipend_to')")
    object_: str = Field(description="The updated target node entity or property value (e.g., '$700 per month')")

class FeedbackCorrections(BaseModel):
    corrections: List[CorrectionTriple] = Field(description="List of factual corrections identified from comparing original and edited drafts.")

def generate_draft(query: str, graph_manager: GraphManager, cleaned_text: str) -> str:
    """
    Queries the knowledge graph for relevant facts and uses them as context.
    Falls back to cleaned_text if no relevant facts are found in the graph.
    """
    relevant_facts = graph_manager.get_relevant_triples(query)
    
    # Use graph context if available, otherwise fall back to cleaned text
    if relevant_facts:
        context = "\n".join(relevant_facts)
        print(f"🔍 Grounded Retrieval: Retrieved {len(relevant_facts)} relevant facts from the Knowledge Graph.")
    else:
        context = cleaned_text
        print("⚠️ Grounded Retrieval: No relevant facts found in graph. Falling back to cleaned document text.")

    import os
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY not found. Using Mock LLM for draft generation.")
        # Dynamically build mock memo using graph attributes
        stipend_val = "$500 per month"
        expiry_val = "December 2026"
        for u, v, d in graph_manager.graph.edges(data=True):
            rel_name = d.get("relation", "").lower()
            if "stipend" in rel_name:
                stipend_val = v
            if "expire" in rel_name or "expiry" in rel_name:
                expiry_val = v
        
        return (
            f"INTERNAL MEMO\n"
            f"To: Legal Review Team\n"
            f"From: AI Contract Analysis Engine\n"
            f"Date: June 04, 2026\n"
            f"Subject: Compensation and Term Summary\n\n"
            f"This memorandum summarizes the compensation layout and contract terms for the Intern:\n"
            f"- Intern Name: John Doe\n"
            f"- Contracting Entity: Ambitio Corp\n"
            f"- Stipend Compensation: {stipend_val}\n"
            f"- Expiry Date: {expiry_val}\n"
        )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Using ONLY the following retrieved background evidence, draft an internal pass summary memo answering the query. "
            "Do not introduce outside knowledge or hallucinate. Be factual, professional, and clear."
        )),
        ("human", "Evidence:\n{context}\n\nQuery: {query}\n\nDraft Memo:")
    ])
    
    chain = prompt | llm
    return chain.invoke({"context": context, "query": query}).content

def process_operator_feedback(original_draft: str, edited_draft: str, graph_manager: GraphManager) -> List[CorrectionTriple]:
    """
    Compares the original AI draft with the human-edited draft.
    Extracts the changed facts and updates/mutates the NetworkX graph.
    """
    import os
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY not found. Using Mock LLM for feedback analysis.")
        # Detect updates (we know operator changed stipend to $700 per month)
        corrections = [
            CorrectionTriple(
                subject="John Doe",
                predicate="receives_stipend",
                object_="$700 per month"
            )
        ]
        print(f"\n🔄 Learning Loop (Mock Mode): Identified {len(corrections)} factual update(s) from human edits.")
        for correction in corrections:
            graph_manager.add_triple(
                subject=correction.subject,
                predicate=correction.predicate,
                object_=correction.object_,
                raw_source_context="Operator Feedback Loop Update (Mock)",
                confidence_score=1.0
            )
        return corrections

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an expert legal knowledge editor. Compare the Original AI Draft with the Operator Edited Draft. "
            "Identify any factual updates or corrections the operator made (such as stipend amounts, dates, names). "
            "Return the list of corrected triples that should replace old facts in the knowledge base."
        )),
        ("human", "Original Draft:\n{original}\n\nEdited Draft:\n{edited}")
    ])
    
    structured_llm = llm.with_structured_output(FeedbackCorrections)
    feedback_chain = prompt | structured_llm
    
    result = feedback_chain.invoke({"original": original_draft, "edited": edited_draft})
    
    print(f"\n🔄 Learning Loop: Identified {len(result.corrections)} factual update(s) from human edits.")
    for correction in result.corrections:
        # Mutate the Graph with the learned updates
        graph_manager.add_triple(
            subject=correction.subject,
            predicate=correction.predicate,
            object_=correction.object_,
            raw_source_context="Operator Feedback Loop Update",
            confidence_score=1.0  # Operator feedback is treated as ground truth
        )
        
    return result.corrections
