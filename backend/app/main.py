from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import date
from typing import List
from pydantic import BaseModel
from app.watchdog.timebar import calculate_timebar, TimeBarRequest, TimeBarResult
from app.retrieval.hybrid import searcher
from app.agents.parsing import parse_notice
from app.agents.graph import app as agent_app
from app.models.schemas import NoticeRequest

app = FastAPI(title="TaxShield API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("🚀 Starting up... Building Search Index...")
    searcher.build_index()

@app.get("/")
def home():
    return {"message": "TaxShield API is running!"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/info")
def project_info():
    return {
        "project": "TaxShield",
        "version": "0.1.0",
        "description": "AI-powered GST notice response system",
        "features": [
            "Time-bar detection",
            "Hybrid RAG search",
            "Multi-agent workflow"
        ],
        "status": "development"
    }

@app.get("/api/timebar", response_model=TimeBarResult)
def timebar(
    fy: str = "2018-19", 
    section: int = 73, 
    notice_date: date = date(2024, 1, 15)
):
    request = TimeBarRequest(fy=fy, section=section, notice_date=notice_date)
    return calculate_timebar(request)

class SearchResult(BaseModel):
    doc_id: str
    text: str
    score: float
    metadata: dict

@app.get("/api/search", response_model=List[SearchResult])
def search_circulars(query: str):
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    results = searcher.search(query)
    return results

@app.get("/api/search/preview", response_class=HTMLResponse)
def search_preview(query: str):
    if not query:
        return "<h1>Please provide a query parameter, e.g. ?query=timebar</h1>"
    
    results = searcher.search(query)
    
    html_content = f"""
    <html>
        <head>
            <title>TaxShield Search Preview</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
                h1 {{ color: #2c3e50; }}
                .card {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .score {{ color: #e67e22; font-weight: bold; float: right; }}
                .highlight {{ background-color: #f1c40f; padding: 0 4px; }}
            </style>
        </head>
        <body>
            <h1>🔍 Search Results for: <i>"{query}"</i></h1>
            <p>Found {len(results)} relevant documents</p>
            <hr>
    """
    
    for r in results:
        html_content += f"""
        <div class="card">
            <span class="score">Score: {r['score']:.4f}</span>
            <h3>📄 {r['doc_id']}</h3>
            <p>{r['text']}</p>
            <small><b>Metadata:</b> {r['metadata']}</small>
        </div>
        """
        
    html_content += "</body></html>"
    return html_content
@app.post("/api/upload-notice")
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
        "extracted_text": notice_text[:200] + "...", # Preview
        "reply": final_state.get("draft_reply"),
        "relevant_laws": [doc['doc_id'] for doc in final_state.get("relevant_docs", [])],
        "confidence": final_state.get("confidence_score"),
        "audit_passed": final_state.get("audit_passed")
    }
