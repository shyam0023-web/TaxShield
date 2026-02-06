"""Drafting Module - Generates legal reply using LLM"""
from app.llm.groq_client import generate
from app.agents.state import AgentState

DRAFT_PROMPT = """You are a legal assistant helping respond to GST notices.
Based on the following retrieved legal documents:
{context}
Draft a professional legal reply for a GST notice with these details:
- Financial Year: {fy}
- Section: {section}
- Notice Content: {notice_text}
Your reply should:
1. Be formal and professional
2. Cite specific circulars and sections
3. Present legal arguments clearly
4. Be concise but comprehensive
Draft Reply:"""

def draft_reply(state: AgentState) -> dict:
    """Generate legal reply using LLM with retrieved context"""
    
    # Format context from retrieved docs
    context = "\n\n".join([
        f"[{doc['doc_id']}]: {doc['text']}"
        for doc in state.get('relevant_docs', [])
    ])
    
    if not context:
        return {
            "draft_reply": "ABSTAIN: Insufficient legal context found.",
            "confidence_score": 0.0,
            "messages": ["No documents found, abstaining from draft"]
        }
    
    # Build prompt
    prompt = DRAFT_PROMPT.format(
        context=context,
        fy=state['fy'],
        section=state['section'],
        notice_text=state['notice_text']
    )
    
    # Generate reply
    reply = generate(prompt)
    
    return {
        "draft_reply": reply,
        "confidence_score": 0.85,
        "messages": ["Draft generated successfully"]
    }
