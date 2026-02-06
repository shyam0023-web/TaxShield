from app.retrieval.hybrid import searcher
from app.agents.state import AgentState

def research(state: AgentState) -> dict:
    query = f"{state['notice_text']} section {state['section']} FY {state['fy']}"
    
    results = searcher.search(query, top_k=5)
    
    relevant_docs = []
    for r in results:
        relevant_docs.append({
            "doc_id": r["doc_id"],
            "text": r["text"],
            "score": r["score"]
        })
    
    return {
        "relevant_docs": relevant_docs,
        "messages": [f"Found {len(relevant_docs)} relevant documents"]
    }
