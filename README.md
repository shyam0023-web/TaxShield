# TaxShield: Agentic RAG for GST Notice Automation

![TaxShield Banner](https://img.shields.io/badge/Status-Development-green) ![License](https://img.shields.io/badge/License-MIT-blue) ![Python](https://img.shields.io/badge/Python-3.11-yellow)

**TaxShield** is an AI-powered legal assistant designed to automate the initial response to GST (Goods and Services Tax) notices in India. It uses an **Agentic RAG (Retrieval Augmented Generation)** architecture to fetch relevant legal circulars, verify limitation periods, and draft professional legal replies.

## 🚀 Key Features

*   **Time-Bar Watchdog**: Automatically calculates limitation periods under Section 73/74 of the CGST Act to dismiss invalid notices instantly.
*   **Hybrid Search**: Combines Dense Vector Search (FAISS) with Keyword Search (BM25) to find the most relevant legal precedents.
*   **Agentic Workflow**: Orchestrated by **LangGraph**, enabling a chain of agents (Parser -> Researcher -> Drafter -> Auditor).
*   **Hallucination Audit**: A dedicated Audit Agent verifies that the drafted reply cites the actual documents retrieved, ensuring legal accuracy.
*   **PDF Parsing**: Upload PDF notices directly for analysis.

## 🏗️ Architecture

The system follows a multi-agent pipeline:
1.  **Parsing Agent**: Extracts text from the uploaded PDF notice.
2.  **Watchdog**: Checks if the notice is time-barred by law.
3.  **Research Agent**: Finds relevant notifications/circulars using Hybrid RAG.
4.  **Drafting Agent**: Uses Llama 3.3 (via Groq) to draft a legal response.
5.  **Audit Agent**: Validates the draft against the retrieved evidence.

## 🛠️ Tech Stack

*   **Backend**: FastAPI, Pydantic
*   **AI/LLM**: LangChain, LangGraph, Groq (Llama 3.3 70B)
*   **RAG**: FAISS (Vector Store), RankBM25
*   **PDF**: pypdf

## ⚡ Getting Started

### Prerequisites
- Python 3.10+
- A [Groq API Key](https://console.groq.com)

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/StartYourAI/Taxshield.git
    cd Taxshield
    ```

2.  **Install dependencies**
    ```bash
    cd backend
    pip install -r requirements.txt
    ```

3.  **Set up Environment**
    Create a `.env` file in the `backend` folder:
    ```ini
    GROQ_API_KEY=your_groq_api_key_here
    ```

4.  **Run the Server**
    ```bash
    python -m uvicorn app.main:app --reload
    ```
    Access the API at `http://127.0.0.1:8000/docs`

## 🤝 Contribution Guidelines

We welcome contributions! Functional areas to work on:

- [ ] **Frontend**: Build a Next.js or Streamlit dashboard.
- [ ] **Data**: Add more GST circulars to `backend/data/circulars`.
- [ ] **Parsers**: Improve PDF extraction for scanned documents (OCR).
- [ ] **Deployment**: Create Dockerfile and deploy scripts.

### How to Contribute
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

## 📜 License
TaxShield is open-source software licensed under the MIT license.