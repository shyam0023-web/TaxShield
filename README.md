# TaxShield: AI-Powered GST Notice Reply Automation

![Python](https://img.shields.io/badge/Python-3.11-yellow) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green) ![Next.js](https://img.shields.io/badge/Next.js-14-black) ![License](https://img.shields.io/badge/License-MIT-blue)

**TaxShield** is an AI-powered GST notice reply automation platform using Agentic RAG with a multi-agent pipeline. It automatically extracts notice details, validates limitation periods, retrieves relevant legal circulars, and drafts professional legal responses with built-in hallucination auditing.

## 🚀 Key Features

- **Time-Bar Watchdog**: Automatically calculates limitation periods under Section 73/74 of the CGST Act to dismiss invalid notices instantly
- **Hybrid RAG Search**: Combines FAISS vector search with BM25 keyword search using Reciprocal Rank Fusion for optimal document retrieval
- **Multi-Agent Pipeline**: Orchestrated 5-agent workflow (Parser → Watchdog → Researcher → Drafter → Auditor) using LangGraph
- **Hallucination Audit**: Citation verification against retrieved documents ensures legal accuracy and prevents fabricated references
- **OCR Support**: Tesseract OCR with OpenCV preprocessing for scanned PDFs when digital text extraction fails
- **Deadline Tracker**: Automatic deadline tracking with reminders at 7 days, 3 days, and 1 day before due dates
- **CA Collaboration**: Shareable review links with 7-day expiry for Chartered Accountant collaboration and approval
- **Regional Languages**: Hindi, Tamil, and Malayalam translation support for reply summaries
- **Notification System**: Persistent notifications with retry logic and deduplication via Redis
- **Reply Strength Scoring**: Automatic strength labeling (strong/supported/weak) based on evidence quality

## 🏗️ Architecture

TaxShield follows a 5-agent pipeline architecture:

1. **Parsing Agent**: Extracts text from uploaded PDF notices with OCR fallback for scanned documents
2. **Time-Bar Watchdog**: Validates notice dates against Section 73/74 limitation periods using pure mathematical calculations
3. **Research Agent**: Performs hybrid RAG search using FAISS + BM25 with Reciprocal Rank Fusion to find relevant GST circulars and notifications
4. **Drafting Agent**: Uses Groq's Llama 3.3 70B model to draft professional legal responses based on retrieved evidence
5. **Audit Agent**: Validates all citations in the draft against actual retrieved documents to prevent hallucinations

The system uses a stateless FastAPI backend with Redis caching and PostgreSQL persistence, ensuring scalability and reliability.

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI, Celery, Redis |
| **Frontend** | Next.js |
| **AI/LLM** | LangChain, LangGraph, Groq (Llama 3.3 70B) |
| **RAG** | FAISS, RankBM25 |
| **Database** | PostgreSQL |
| **PDF Processing** | pypdf + Tesseract OCR |
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

## 📜 License
TaxShield is open-source software licensed under the MIT license.