"""AgentState schema for LangGraph workflow"""
from typing import TypedDict, List, Optional
class AgentState(TypedDict):
    notice_text: str
    fy: str
    section: int
    is_time_barred: bool
    relevant_laws: List[str]
    draft_reply: str
    confidence_score: float
    audit_passed: bool
