"""
TaxShield — Notices Routes
Purpose: PDF upload and notice processing endpoints
Status: IMPLEMENTED
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.agents.parsing import parse_notice
from app.agents.graph import app as agent_app
from app.logger import logger

router = APIRouter()


@router.post("/notices/upload")
async def upload_notice(
    file: UploadFile = File(...),
    fy: str = Form(...),
    section: int = Form(...)
):
    """Upload PDF -> Parse -> Run Agents"""
    
    # 1. Read & Parse PDF
    content = await file.read()
    notice_text = parse_notice(content)
    
    if not notice_text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")
    
    # 2. Setup State
    initial_state = {
        "notice_text": notice_text,
        "fy": fy,
        "section": section,
        "is_time_barred": False,
        "relevant_docs": [],
        "draft_reply": "",
        "confidence_score": 0.0,
        "audit_passed": False,
        "messages": []
    }
    
    # 3. Run Agents
    final_state = await agent_app.ainvoke(initial_state)
    
    return {
        "extracted_text": notice_text[:200] + "...",
        "reply": final_state.get("draft_reply"),
        "relevant_laws": [doc['doc_id'] for doc in final_state.get("relevant_docs", [])],
        "confidence": final_state.get("confidence_score"),
        "audit_passed": final_state.get("audit_passed")
    }


@router.get("/notices/{id}")
def get_notice(id: str):
    """Get notice by ID"""
    # TODO: Implement notice retrieval from database
    return {"notice_id": id, "status": "PLACEHOLDER"}
