# TaxShield: AI-Powered GST Notice Reply Automation

![Python](https://img.shields.io/badge/Python-3.11-yellow) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green) ![Next.js](https://img.shields.io/badge/Next.js-14-black)

**TaxShield** is an AI-powered GST notice reply automation platform using a multi-agent system with risk-based routing. It extracts notice details (including scanned documents), redacts sensitive PII, classifies risk level, interviews clients for missing facts via live chat, and drafts professional legal responses with citation verification.

## 🚀 Key Features

- **Risk-Based Routing**: Classifies notices as LOW/MEDIUM/HIGH risk — simple notices get fast template replies, complex cases get full legal analysis
- **Live Agent Chat**: Real-time conversational agent that interviews clients, searches case laws mid-conversation, and shows its reasoning
- **Time-Bar Watchdog**: Automatically calculates limitation periods under Section 73/74 of the CGST Act to dismiss invalid notices instantly
- **Hybrid RAG Search**: Combines FAISS vector search with BM25 keyword search using Reciprocal Rank Fusion for optimal document retrieval
- **PII Redaction**: In-memory redaction of PAN/Aadhaar before any data reaches the LLM — DPDP Act compliant
- **OCR Support**: PaddleOCR for Hindi+English scanned notices with OpenCV preprocessing
- **Citation Audit**: Every case law reference in the draft is validated against the actual retrieved documents — prevents hallucinated citations
- **Deadline Tracker**: Automatic deadline tracking with reminders at 7 days, 3 days, and 1 day before due dates
- **Professional Output**: Generates `.docx` reply drafts + computation sheets + cover letters
- **Notification System**: Persistent notifications with retry logic and deduplication via Redis

## 🏗️ Architecture

TaxShield uses a **4-agent architecture with risk-based routing**:

1. **Document Processor**: OCR extraction (PaddleOCR), PII redaction, time-bar validation — no LLM needed
2. **Risk Router**: Classifies notice risk (LOW/MEDIUM/HIGH) based on amount, sections, and penalty language
3. **Legal Analyst** (Live Agent): ReAct agent that interviews clients in real-time, searches case laws and circulars via RAG, and builds defense strategies
4. **Master Drafter**: Formats strategy into professional legal documents with citation validation and completeness checks

The system uses a stateless FastAPI backend with Redis caching and PostgreSQL persistence. Risk-based routing ensures simple notices are handled in seconds while complex cases get thorough analysis.

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI, Celery, Redis |
| **Frontend** | Next.js |
| **AI/LLM** | LangChain, LangGraph, Gemini 2.0 Flash / Pro |
| **RAG** | FAISS + BM25 (circulars), Qdrant (case laws) |
| **OCR** | PaddleOCR (Hindi+English) |
| **Database** | PostgreSQL |
| **Document Output** | python-docx, openpyxl |
| **Authentication** | JWT + PostgreSQL RLS |

## ⚡ Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis

### Installation

1. **Clone the repository**
    ```bash
    git clone https://github.com/StartYourAI/Taxshield.git
    cd Taxshield
    ```

2. **Install backend dependencies**
    ```bash
    cd backend
    pip install -r requirements.txt
    ```

3. **Install frontend dependencies**
    ```bash
    cd ../frontend
    npm install
    ```

4. **Set up Environment**
    Create a `.env` file in the `backend` folder:
    ```ini
    GROQ_API_KEY=your_groq_api_key_here
    REDIS_URL=redis://localhost:6379
    DATABASE_URL=postgresql://user:password@localhost/taxshield
    ```

5. **Run the services**
    ```bash
    # Terminal 1: Start Redis
    redis-server
    
    # Terminal 2: Start PostgreSQL (if not running as service)
    postgres
    
    # Terminal 3: Start Celery worker
    cd backend
    celery -A app.celery worker --loglevel=info
    
    # Terminal 4: Start FastAPI backend
    cd backend
    python -m uvicorn app.main:app --reload
    
    # Terminal 5: Start Next.js frontend
    cd frontend
    npm run dev
    ```

6. **Access the application**
    - Frontend: `http://localhost:3000`
    - API Documentation: `http://localhost:8000/docs`

## 🤝 Contribution Guidelines

We welcome contributions! Key areas to work on:

- [ ] **Frontend**: Enhance the Next.js dashboard with improved UX
- [ ] **Data**: Add more GST circulars to `backend/data/circulars`
- [ ] **OCR**: Improve Tesseract preprocessing for better scanned document accuracy
- [ ] **Localization**: Add more regional languages and improve translations
- [ ] **Testing**: Add comprehensive unit and integration tests
- [ ] **Documentation**: Improve API documentation and user guides

### How to Contribute
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
