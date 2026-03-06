"""
TaxShield — Agent State
Purpose: TypedDict for shared pipeline state across 4-agent workflow
Status: IMPLEMENTED
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from operator import add


class AgentState(TypedDict):
    # Input from notice upload
    notice_text: str
    fy: str
    section: int
    case_id: Optional[str]
    
    # Agent 1: Document Processor output
    extracted_entities: Dict[str, Any]
    time_bar_status: bool
    document_structure: Dict[str, str]
    
    # Agent 2: Risk Router output
    risk_classification: str  # LOW/MEDIUM/HIGH
    confidence_score: float
    
    # Agent 3: Legal Analyst output
    relevant_circulars: List[Dict[str, Any]]
    relevant_case_laws: List[Dict[str, Any]]
    legal_analysis: str
    client_interview: List[Dict[str, str]]
    
    # Agent 4: Master Drafter output
    draft_reply: str
    defense_strategy: str
    supporting_documents: List[str]
    procedural_compliance: bool
    
    # Shared state
    messages: Annotated[List[Dict[str, Any]], add]
    audit_passed: bool
    error: Optional[str]
    metadata: Dict[str, Any]
