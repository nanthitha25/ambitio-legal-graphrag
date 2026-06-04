import networkx as nx
from typing import List, Optional, Tuple, Dict, Any

class GraphManager:
    def __init__(self):
        self.graph = nx.DiGraph()

    def _normalize_string(self, text: str) -> str:
        return text.strip().lower().replace("_", " ").replace("-", " ")

    def are_relations_similar(self, rel1: str, rel2: str) -> bool:
        """
        Determines if two relations are similar based on exact match,
        token overlap, or key domain-specific words.
        """
        r1 = self._normalize_string(rel1)
        r2 = self._normalize_string(rel2)
        if r1 == r2:
            return True
        
        stop_words = {"to", "of", "for", "in", "on", "at", "by", "with", "a", "an", "the", "has", "is", "are"}
        words1 = {w for w in r1.split() if w not in stop_words}
        words2 = {w for w in r2.split() if w not in stop_words}
        
        # Domain-specific terms that represent unique singular facts
        key_words = {"stipend", "expiry", "expires", "pay", "payment", "compensation", "salary", "date"}
        shared = words1.intersection(words2)
        if shared:
            # If any shared word is a key word, they represent the same relationship concept
            if shared.intersection(key_words):
                return True
            # Otherwise check for high overlap
            if len(shared) / max(len(words1), len(words2)) >= 0.5:
                return True
        return False

    def add_triple(self, subject: str, predicate: str, object_: str, 
                   raw_source_context: Optional[str] = None, 
                   confidence_score: Optional[float] = None, 
                   **properties) -> None:
        """
        Adds a triple to the graph, resolving any conflicting edges.
        """
        # Resolve conflicting relations
        edges_to_remove = []
        for u, v, data in self.graph.out_edges(subject, data=True):
            existing_relation = data.get("relation", "")
            if self.are_relations_similar(existing_relation, predicate):
                # If target is different, it's a conflict (e.g., stipend amount changed from $500 to $700)
                if v != object_:
                    edges_to_remove.append((u, v, existing_relation))

        for u, v, rel in edges_to_remove:
            print(f"🗑️ Deleting conflicting relation: '{u}' --({rel})--> '{v}'")
            self.graph.remove_edge(u, v)
            # Clean up orphaned nodes
            if self.graph.degree(v) == 0:
                self.graph.remove_node(v)
                print(f"🧹 Cleaned up orphaned value node: '{v}'")

        # Add or update edge
        # Merge properties
        edge_data = {
            "relation": predicate,
            "raw_source_context": raw_source_context,
            "confidence_score": confidence_score
        }
        edge_data.update(properties)
        
        self.graph.add_edge(subject, object_, **edge_data)
        print(f"➕ Added edge: '{subject}' --({predicate})--> '{object_}' (Confidence: {confidence_score})")

    def get_relevant_triples(self, query: str) -> List[str]:
        """
        Retrieves relevant graph edges based on semantic matches with the query.
        """
        query_norm = self._normalize_string(query)
        relevant_facts = []
        for u, v, d in self.graph.edges(data=True):
            u_norm = self._normalize_string(u)
            v_norm = self._normalize_string(v)
            rel_norm = self._normalize_string(d.get("relation", ""))
            
            # Check if query words appear in subject, object, or relation
            if (query_norm in u_norm or 
                query_norm in v_norm or 
                query_norm in rel_norm or
                any(word in u_norm or word in v_norm or word in rel_norm for word in query_norm.split() if len(word) > 3)):
                
                context_str = f" [Context: '{d['raw_source_context']}']" if d.get('raw_source_context') else ""
                relevant_facts.append(f"- {u} -> {d['relation']} -> {v}{context_str}")
        return relevant_facts

    def visualize(self) -> None:
        """
        Prints the current graph representation.
        """
        print("\n--- Current Knowledge Graph ---")
        if self.graph.number_of_edges() == 0:
            print("(Graph is empty)")
        for u, v, d in self.graph.edges(data=True):
            print(f"  {u} --({d['relation']})--> {v} (conf: {d.get('confidence_score')})")
        print("--------------------------------\n")
