import streamlit as st
import networkx as nx
from src.processor import clean_and_extract
from src.graph_manager import GraphManager
from src.generator import generate_draft, process_operator_feedback

# --- PAGE CONFIG & SESSION STATE ---
st.set_page_config(page_title="Ambitio Legal GraphRAG", layout="wide", page_icon="📋")
st.title("📋 Ambitio Adaptive Legal GraphRAG Pipeline")
st.caption("Ingest messy documents, explore deterministic knowledge graphs, and update the system via live edits.")

# Persist the GraphManager across UI interactions
if "graph_manager" not in st.session_state:
    st.session_state.graph_manager = GraphManager()
if "cleaned_text" not in st.session_state:
    st.session_state.cleaned_text = ""
if "current_draft" not in st.session_state:
    st.session_state.current_draft = ""

# --- SIDEBAR: INPUT DOCUMENT ---
with st.sidebar:
    st.header("1. Document Ingestion")
    
    # Provide the default messy sample text
    default_text = """AMENDMNT TO AGRMNT
Ths agreement made on 04th of June, 2026 (the "Effctive Date") by and btween 
Ambitio Corp (herein "The Compny") and John Doe ("The Intern").
SECTION 4: Compensation layout. The Compny agrees to pay the Intern a stpnd 
of $500 per month. Expiry date of this current clause is set for December 2026."""
    
    doc_input = st.text_area("Paste Raw/Messy Legal Text:", value=default_text, height=250)
    
    if st.button("Process & Build Graph", type="primary"):
        with st.spinner("Extracting triples and constructing in-memory graph..."):
            # Execute Step 1 parsing
            extracted_data = clean_and_extract(doc_input)
            
            # Reset and populate the graph
            st.session_state.graph_manager = GraphManager()
            for triple in extracted_data.triples:
                st.session_state.graph_manager.add_triple(
                    triple.subject, triple.predicate, triple.object_,
                    raw_source_context=triple.raw_source_context,
                    confidence_score=triple.confidence_score
                )
            
            st.session_state.cleaned_text = extracted_data.cleaned_text
            st.success("Graph constructed successfully!")

# --- MAIN INTERFACE SPLIT ---
col1, col2 = st.columns([1, 1])

with col1:
    st.header("🕸️ Knowledge Graph State")
    if st.session_state.cleaned_text:
        st.subheader("Extracted Triples:")
        # Display the graph edges inside a clean table
        edges = []
        for u, v, d in st.session_state.graph_manager.graph.edges(data=True):
            edges.append({
                "Subject": u, 
                "Relationship": d.get("relation", ""), 
                "Object": v,
                "Confidence": d.get("confidence_score", 1.0)
            })
        
        if edges:
            st.table(edges)
        else:
            st.info("Graph is currently empty.")
    else:
        st.info("Ingest a document on the sidebar to populate the graph.")

with col2:
    st.header("📝 Memo Generation & Editing Loop")
    
    if st.session_state.cleaned_text:
        query = st.text_input("Enter Prompt / Query:", value="What is the stipend amount and expiry date?")
        
        if st.button("Generate Draft Memo"):
            with st.spinner("Retrieving from graph and drafting..."):
                draft = generate_draft(query, st.session_state.graph_manager, st.session_state.cleaned_text)
                st.session_state.current_draft = draft

        if st.session_state.current_draft:
            st.subheader("AI Generated Draft (Editable):")
            # This text area allows the user to act as the human operator and modify the facts live
            edited_draft = st.text_area("Review and edit the draft below:", value=st.session_state.current_draft, height=220)
            
            if st.button("Submit Operator Edits (Learning Loop)"):
                with st.spinner("Processing feedback & mutating graph..."):
                    # 1. Update the underlying graph data structure
                    process_operator_feedback(st.session_state.current_draft, edited_draft, st.session_state.graph_manager)
                    
                    st.toast("Graph mutated successfully! Old facts cleared.", icon="🔄")
                    
                    # 2. CRITICAL FIX: Force the LLM to write a brand new draft using the updated graph facts
                    updated_draft = generate_draft(query, st.session_state.graph_manager, st.session_state.cleaned_text)
                    
                    # 3. Save the newly generated text to state and force a UI re-render
                    st.session_state.current_draft = updated_draft
                    st.rerun()
    else:
        st.info("The generation engine will become active once data is loaded into the graph.")
