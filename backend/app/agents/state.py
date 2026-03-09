"""
TaxShield — Pipeline State
TypedDict for shared state across all 4 agents.
"""
from typing import TypedDict, Optional, Any

class PipelineState(TypedDict, total=False):
    # Input
    pdf_bytes: bytes
    case_id: str
    
    # Agent 1 output
    raw_text: str
    ocr_metadata: dict
    entities: dict
    notice_annotations: list
    time_bar: dict
    redacted_fields: list
    
    # Agent 2 output
    risk_level: str         # LOW, MEDIUM, HIGH
    risk_score: float       # 0-1
    risk_reasoning: str
    deadline: dict          # {days_left, urgency}
    is_time_barred: bool    # Final decision (by Agent 2)
    
    # Agent 3 output  
    interview_answers: dict
    retrieved_circulars: list
    retrieved_case_laws: list
    defense_strategy: Optional[str]
    
    # Agent 4 output
    draft_docx_path: Optional[str]
    draft_xlsx_path: Optional[str]
    cover_letter_path: Optional[str]
    citation_report: Optional[dict]
    accuracy_report: Optional[dict]
    
    # Metadata
    human_review_notes: str
    escalation_history: list
    current_agent: str
