from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# 1. Define the structural target using Pydantic
class KnowledgeTriple(BaseModel):
    subject: str = Field(description="The source node entity (e.g., 'Ambitio Corp', 'John Doe')")
    predicate: str = Field(description="The relationship or action connecting the nodes (e.g., 'pays_stipend_to', 'expires_on')")
    object_: str = Field(description="The target node entity or property value (e.g., '$500', 'December 2026')")
    raw_source_context: Optional[str] = Field(description="The exact snippet of text this fact was extracted from to guarantee grounding")
    confidence_score: Optional[float] = Field(description="A confidence score between 0.0 (low certainty) and 1.0 (absolute certainty) for this extraction")

class ExtractedContractData(BaseModel):
    cleaned_text: str = Field(description="The fully reconstructed text, with typos fixed and clear structural formatting.")
    triples: List[KnowledgeTriple] = Field(description="The list of structured graph relationships extracted from the document.")

# 2. Implementation function
def clean_and_extract(text: str) -> ExtractedContractData:
    import os
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY not found. Using Mock LLM for cleaning and extraction.")
        return ExtractedContractData(
            cleaned_text=(
                "AMENDMENT TO AGREEMENT\n"
                "This agreement made on 04th of June, 2026 (the \"Effective Date\") by and between "
                "Ambitio Corp (herein \"The Company\") and John Doe (\"The Intern\").\n"
                "SECTION 4: Compensation layout. The Company agrees to pay the Intern a stipend "
                "of $500 per month. Expiry date of this current clause is set for December 2026."
            ),
            triples=[
                KnowledgeTriple(
                    subject="Ambitio Corp",
                    predicate="agreement_with",
                    object_="John Doe",
                    raw_source_context="by and between Ambitio Corp ... and John Doe",
                    confidence_score=0.95
                ),
                KnowledgeTriple(
                    subject="John Doe",
                    predicate="receives_stipend",
                    object_="$500 per month",
                    raw_source_context="pay the Intern a stipend of $500 per month",
                    confidence_score=0.98
                ),
                KnowledgeTriple(
                    subject="SECTION 4",
                    predicate="expires_on",
                    object_="December 2026",
                    raw_source_context="Expiry date of this current clause is set for December 2026",
                    confidence_score=0.92
                )
            ]
        )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an elite legal data parsing agent. Your job is twofold:\n"
            "1. Clean up the incoming messy text (fix typos, bad line breaks, and clear up ambiguity).\n"
            "2. Extract atomic semantic relationships as [Subject, Predicate, Object] triples for a knowledge graph. "
            "Ensure you populate confidence scores and exact text snippets as source context for grounding."
        )),
        ("human", "Messy Document Input:\n\n{text}")
    ])
    
    # Enforce structured output parsing matching our schema
    structured_llm = llm.with_structured_output(ExtractedContractData)
    extractor_chain = prompt | structured_llm
    
    return extractor_chain.invoke({"text": text})
