from typing import TypedDict, List, Annotated
from operator import add

class AgentState(TypedDict):
    notice_text: str
    fy: str
    section: int
    
    is_time_barred: bool
    relevant_docs: Annotated[List[dict], add]
    
    draft_reply: str
    confidence_score: float
    audit_passed: bool
    
    messages: Annotated[List[str], add]
