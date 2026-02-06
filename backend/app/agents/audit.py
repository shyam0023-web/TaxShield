from app.agents.state import AgentState

def audit(state: AgentState) -> dict:
    draft = state.get("draft_reply", "")
    found_docs = state.get("relevant_docs", [])
    found_ids = [doc['doc_id'] for doc in found_docs]
    
    citation_count = 0
    for doc_id in found_ids:
        if doc_id in draft:
            citation_count += 1
            
    if len(found_docs) > 0:
        score = citation_count / len(found_docs)
    else:
        score = 1.0 if "ABSTAIN" in draft else 0.0
        
    score = min(score, 1.0)
    
    passed = score >= 0.5
    
    return {
        "confidence_score": score,
        "audit_passed": passed,
        "messages": [f"Audit: {'PASSED' if passed else 'FAILED'} (Score: {score:.2f})"]
    }
