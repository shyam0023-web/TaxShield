from fastapi import FastAPI, HTTPException
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
