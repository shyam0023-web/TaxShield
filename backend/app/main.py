from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from datetime import date
from typing import List
from pydantic import BaseModel
from app.watchdog.timebar import calculate_timebar, TimeBarRequest, TimeBarResult
from app.retrieval.hybrid import searcher

app = FastAPI(title="TaxShield API")

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
