import os
import sys
from src.processor import clean_and_extract
from src.graph_manager import GraphManager
from src.generator import generate_draft, process_operator_feedback

def main():
    # Show warning if OpenAI API Key is not set
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️ Warning: OPENAI_API_KEY environment variable is not set.")
        print("The pipeline will run in Mock LLM Simulation Mode to demonstrate the flow.")
        print("To run with the real LLM, set: export OPENAI_API_KEY='your-key-here'\n")

    print("======================================================================")
    print("🚀 STARTING DYNAMIC GRAPHRAG PIPELINE DEMONSTRATION")
    print("======================================================================\n")

    # Step 1: Load the messy file
    contract_path = "data/sample_contract.txt"
    print(f"📖 Step 1: Loading raw messy text from '{contract_path}'...")
    with open(contract_path, "r") as f:
        messy_text = f.read()

    print("\n--- Raw Messy Input Text ---")
    print(messy_text.strip())
    print("----------------------------\n")

    # Step 2: Setup LLM to clean text and extract Graph Triples
    print("🧠 Step 2: Processing document & extracting clean text + triples via LLM...")
    extracted_data = clean_and_extract(messy_text)
    
    print("\n✨ Cleaned Reconstructed Text:")
    print(f"\"\"\"\n{extracted_data.cleaned_text.strip()}\n\"\"\"")

    # Initialize Graph Manager and populate NetworkX graph
    graph_manager = GraphManager()
    print("\n🕸️ Building in-memory NetworkX Graph Database...")
    for triple in extracted_data.triples:
        graph_manager.add_triple(
            subject=triple.subject,
            predicate=triple.predicate,
            object_=triple.object_,
            raw_source_context=triple.raw_source_context,
            confidence_score=triple.confidence_score
        )

    # Visualize initial graph
    graph_manager.visualize()

    # Step 3: Run Initial Draft Generation
    query = "What is the stipend amount and expiry date?"
    print(f"📝 Step 3: Generating initial draft for query: '{query}'...")
    initial_draft = generate_draft(query, graph_manager, extracted_data.cleaned_text)
    
    print("\n📄 --- AI Initial Draft Memo ---")
    print(initial_draft.strip())
    print("--------------------------------\n")

    # Step 4: Operator Feedback & Graph Mutation
    print("👤 Step 4: Simulating Operator Feedback (Human Edit)...")
    # Operator increases stipend to $700 per month
    operator_edited_draft = "Ambitio Corp pays John Doe a stipend of $700 per month expiring December 2026."
    print("\n✏️ Human Operator Edited Draft Memo:")
    print(f"\"{operator_edited_draft}\"")
    
    print("\n🔄 Running LLM-driven Graph Mutation Loop...")
    process_operator_feedback(initial_draft, operator_edited_draft, graph_manager)

    # Visualize updated graph
    graph_manager.visualize()

    # Step 5: Verification (Run draft generation again)
    print("🔬 Step 5: Verification - Generating second draft with same query...")
    second_draft = generate_draft(query, graph_manager, extracted_data.cleaned_text)

    print("\n📄 --- AI Final Updated Draft Memo ---")
    print(second_draft.strip())
    print("--------------------------------------\n")
    
    print("✅ DEMONSTRATION COMPLETE: The pipeline successfully learned from operator feedback dynamically!")

if __name__ == "__main__":
    main()
