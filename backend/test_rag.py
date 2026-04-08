"""
TaxShield — Guardrailed RAG System Test & Usage Guide
"""

import os
import requests
import json
from typing import Dict, Any

# ═══════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════

BASE_URL = "http://localhost:8000/api/rag"
AUTH_TOKEN = "your-jwt-token-here"  # Get from /api/auth/login

HEADERS = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
}


# ═══════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════

def log_response(action: str, resp: requests.Response):
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"[{action}] Status: {resp.status_code}")
    print(f"{'='*60}")
    try:
        data = resp.json()
        print(json.dumps(data, indent=2))
    except:
        print(resp.text)


# ═══════════════════════════════════════════
# Test Scenarios
# ═══════════════════════════════════════════

def test_upload_document():
    """
    Test: Upload a sample document
    """
    print("\n[TEST] Uploading document...")
    
    # Create sample tax circular document
    sample_doc = """
    CBIC Circular No. 42/2023-Cus
    
    Subject: Clarification on GST Input Tax Credit for imported goods
    
    With effect from 1st July 2023, the following goods are eligible for full ITC:
    - Raw materials for manufacture of pharmaceuticals (HS Code 3004-3006)
    - Components for renewable energy systems (HS Code 8503-8504)
    - Electronic components and semiconductors (HS Code 8542-8543)
    
    Conditions:
    1. All imported goods must have accompanying invoices with ITC eligibility mark
    2. Importer must be registered under GST Act
    3. Documentation must be maintained for 5 years
    
    Exemptions:
    - Capital goods with depreciation below 20%
    - Goods for personal use of employees
    - Cosmetic items and luxury goods
    
    Effective Date: 1st July 2023
    """
    
    files = {
        "file": ("sample_circular.txt", sample_doc, "text/plain"),
    }
    
    data = {
        "title": "CBIC Circular 42/2023 - GST ITC Clarification",
        "source_url": "https://cbic.gov.in/resources/htdocs-cbec/customs/circulars/2023/42/index.html",
        "document_type": "circular",
    }
    
    resp = requests.post(
        f"{BASE_URL}/upload",
        files=files,
        data=data,
        headers=HEADERS,
    )
    
    log_response("UPLOAD_DOCUMENT", resp)
    
    if resp.status_code == 200:
        doc_id = resp.json()["doc_id"]
        return doc_id
    
    return None


def test_list_documents():
    """
    Test: List all uploaded documents
    """
    print("\n[TEST] Listing documents...")
    
    resp = requests.get(
        f"{BASE_URL}/documents",
        headers=HEADERS,
    )
    
    log_response("LIST_DOCUMENTS", resp)
    
    return resp.json() if resp.status_code == 200 else None


def test_query_documents(question: str):
    """
    Test: Query documents with guardrailed LLM
    
    Example questions:
    - "What is the GST ITC eligibility criteria for imported goods?"
    - "Which goods are exempted from ITC?"
    - "What is the effective date of the circular?"
    """
    print(f"\n[TEST] Querying documents: '{question}'...")
    
    payload = {
        "question": question,
        "top_k": 5,
        "similarity_threshold": 0.3,
    }
    
    resp = requests.post(
        f"{BASE_URL}/query",
        json=payload,
        headers=HEADERS,
    )
    
    log_response("QUERY_DOCUMENTS", resp)
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"\n[ANALYSIS]")
        print(f"  Answer: {result['answer']}")
        print(f"  Confidence: {result['confidence']:.1%}")
        print(f"  Sources cited: {len(result['sources'])}")
        print(f"  Chunks used: {len(result['chunks_used'])}")
        for src in result['sources']:
            print(f"    - {src}")
    
    return resp.json() if resp.status_code == 200 else None


def test_get_document(doc_id: str):
    """
    Test: Retrieve a specific document
    """
    print(f"\n[TEST] Getting document {doc_id}...")
    
    resp = requests.get(
        f"{BASE_URL}/document/{doc_id}",
        headers=HEADERS,
    )
    
    log_response("GET_DOCUMENT", resp)
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\n[DOCUMENT INFO]")
        print(f"  Chunks: {data['metadata']['chunks_count']}")
        print(f"  Created: {data['metadata']['created_at']}")
        print(f"  Content preview: {data['content'][:200]}...")
    
    return resp.json() if resp.status_code == 200 else None


def test_store_stats():
    """
    Test: Get vector store statistics
    """
    print("\n[TEST] Getting store stats...")
    
    resp = requests.get(
        f"{BASE_URL}/stats",
        headers=HEADERS,
    )
    
    log_response("STORE_STATS", resp)
    
    if resp.status_code == 200:
        stats = resp.json()
        print(f"\n[STORE STATS]")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"  Total chunks: {stats['total_chunks']}")
        print(f"  Total vectors: {stats['total_vectors']}")
        print(f"  Embedding dimension: {stats['embedding_dimension']}")


def test_delete_document(doc_id: str):
    """
    Test: Delete a document
    """
    print(f"\n[TEST] Deleting document {doc_id}...")
    
    resp = requests.delete(
        f"{BASE_URL}/document/{doc_id}",
        headers=HEADERS,
    )
    
    log_response("DELETE_DOCUMENT", resp)
    
    return resp.json() if resp.status_code == 200 else None


# ═══════════════════════════════════════════
# Full Test Sequence
# ═══════════════════════════════════════════

def run_full_test():
    """
    Run comprehensive RAG system test
    """
    print("\n" + "="*80)
    print("TaxShield Guardrailed RAG System — Full Test Suite")
    print("="*80)
    
    # 1. Upload document
    print("\n[Step 1] Upload Document")
    doc_id = test_upload_document()
    if not doc_id:
        print("ERROR: Upload failed. Check token and server.")
        return
    
    # 2. List documents
    print("\n[Step 2] List Documents")
    test_list_documents()
    
    # 3. Get document details
    print("\n[Step 3] Get Document Details")
    test_get_document(doc_id)
    
    # 4. Get stats
    print("\n[Step 4] Store Statistics")
    test_store_stats()
    
    # 5. Query documents with various questions
    print("\n[Step 5] Query Documents")
    test_questions = [
        "What goods are eligible for GST ITC?",
        "What is the effective date?",
        "What are the conditions for ITC eligibility?",
        "Which goods are exempted?",
    ]
    
    for q in test_questions:
        test_query_documents(q)
    
    # 6. Delete document
    print("\n[Step 6] Delete Document")
    test_delete_document(doc_id)
    
    # 7. Verify deletion
    print("\n[Step 7] Verify Deletion")
    test_list_documents()
    
    print("\n" + "="*80)
    print("Test Suite Complete!")
    print("="*80)


# ═══════════════════════════════════════════
# Quick Start Examples
# ═══════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "upload":
            test_upload_document()
        elif command == "list":
            test_list_documents()
        elif command == "query":
            question = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "What is this document about?"
            test_query_documents(question)
        elif command == "stats":
            test_store_stats()
        elif command == "full":
            run_full_test()
        else:
            print(f"Unknown command: {command}")
            print("Available: upload, list, query, stats, full")
    else:
        # Default: run full test
        run_full_test()
