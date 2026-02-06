from pydantic import BaseModel
from typing import List, Optional

class NoticeRequest(BaseModel):
    notice_text: str
    fy: str
    section: int

class DraftResponse(BaseModel):
    draft_reply: str
    confidence_score: float
    citations: List[str]
