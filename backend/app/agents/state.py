"""AgentState schema for LangGraph workflow"""
from typing import TypedDict, List, Optional, Annotated
from operator import add

class AgentState(TypedDict):
    # Input fields
    notice_text: str
    fy: str
    section: int
    
    # Processing fields
    is_time_barred: bool
    relevant_docs: Annotated[List[dict], add]  # Retrieved documents
    
    # Output fields
    draft_reply: str
    confidence_score: float
    audit_passed: bool
    
    # Memory
    messages: Annotated[List[str], add]  # Conversation history
