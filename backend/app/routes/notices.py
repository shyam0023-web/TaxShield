"""
TaxShield — Notices Routes
Purpose: PDF upload and notice processing endpoints
Status: PLACEHOLDER — wired to graph but agents are stubs
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.agents.graph import graph
from app.logger import logger

router = APIRouter()


@router.post("/notices/upload")
async def upload_notice(file: UploadFile = File(...)):
    """Upload PDF → Run 4-agent pipeline"""
    content = await file.read()
    
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    # Run the agent pipeline
    initial_state = {
        "pdf_bytes": content,
        "case_id": file.filename or "unknown",
        "current_agent": "start"
    }
    
    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.exception("Agent pipeline failed")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    return {
        "case_id": final_state.get("case_id"),
        "risk_level": final_state.get("risk_level", "UNKNOWN"),
        "current_agent": final_state.get("current_agent"),
        "status": "processed"
    }


@router.get("/notices/{id}")
def get_notice(id: str):
    """Get notice by ID"""
    return {"notice_id": id, "status": "PLACEHOLDER"}
