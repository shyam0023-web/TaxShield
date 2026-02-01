# TaxShield Backend

AI-powered GST notice response system using Hybrid RAG.

## Features
- Time-bar detection (Section 73/74)
- Hybrid Search (FAISS + BM25 + RRF)
- Multi-agent workflow (coming soon)

## Tech Stack
- FastAPI
- FAISS + BM25
- Python 3.11

## Run Locally
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API Endpoints
- `GET /` - Health check
- `GET /api/timebar` - Calculate limitation period
- `GET /api/search` - Search legal circulars
