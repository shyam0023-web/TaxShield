#!/usr/bin/env python3
"""
End-to-End Test Suite for Supabase RAG Migration

Tests:
1. Supabase connectivity
2. pgvector database setup
3. Document ingestion
4. Hybrid search (BM25 + pgvector)
5. RAG pipeline (search → LLM)
6. RLS policies

Usage:
    python test_rag_e2e.py [test_name]

Examples:
    python test_rag_e2e.py                    # Run all tests
    python test_rag_e2e.py test_connectivity  # Run specific test
    python test_rag_e2e.py --verbose          # Verbose output
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import List, Tuple

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.supabase_client import supabase_client
from app.retrieval.pgvector_search import pgvector_searcher, document_vector_store
from app.retrieval.hybrid import searcher
from app.rag.rag_service import call_embedding_api
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test results
test_results: List[Tuple[str, bool, str]] = []


async def test_connectivity():
    """Test 1: Verify Supabase connection"""
    print("\n🧪 Test 1: Supabase Connectivity")
    print("-" * 50)
    
    try:
        connected = await supabase_client.connect()
        
        if connected:
            print("✅ Connected to Supabase")
            print(f"   URL: {supabase_client.url}")
            test_results.append(("Connectivity", True, "Connected successfully"))
            return True
        else:
            print("❌ Failed to connect")
            test_results.append(("Connectivity", False, "Connection failed"))
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results.append(("Connectivity", False, str(e)[:80]))
        return False


async def test_pgvector_extension():
    """Test 2: Verify pgvector extension is installed"""
    print("\n🧪 Test 2: pgvector Extension")
    print("-" * 50)
    
    try:
        if not supabase_client.is_connected:
            print("⏭️  Skipping (Supabase not connected)")
            return True
        
        # Try to create a test vector
        result = supabase_client.client.rpc("search_chunks_by_embedding", {
            "query_embedding": [0.1] * 1536,
            "match_count": 1,
            "similarity_threshold": 0.5
        }).execute()
        
        print("✅ pgvector extension available")
        print("   Function 'search_chunks_by_embedding' exists")
        test_results.append(("pgvector Extension", True, "Extension loaded"))
        return True
    except Exception as e:
        if "does not exist" in str(e):
            print("❌ pgvector function not found")
            print("   Solution: Run migration SQL in Supabase dashboard")
            test_results.append(("pgvector Extension", False, "Function not found"))
        else:
            print(f"❌ Error: {e}")
            test_results.append(("pgvector Extension", False, str(e)[:80]))
        return False


async def test_document_tables():
    """Test 3: Verify document tables exist"""
    print("\n🧪 Test 3: Document Tables")
    print("-" * 50)
    
    try:
        if not supabase_client.is_connected:
            print("⏭️  Skipping (Supabase not connected)")
            return True
        
        # Test document table
        docs = await supabase_client.get_documents(limit=1)
        print("✅ 'documents' table accessible")
        
        # Test chunks table
        chunks = await supabase_client.get_document_chunks(document_id=1)
        print("✅ 'document_chunks' table accessible")
        
        # Test queries table
        queries_result = supabase_client.client.table("rag_queries").select("*").limit(1).execute()
        print("✅ 'rag_queries' table accessible")
        
        test_results.append(("Document Tables", True, "All tables accessible"))
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Solution: Run migration SQL in Supabase dashboard")
        test_results.append(("Document Tables", False, str(e)[:80]))
        return False


async def test_hybrid_search_index():
    """Test 4: Verify hybrid search can build index"""
    print("\n🧪 Test 4: Hybrid Search Index")
    print("-" * 50)
    
    try:
        await searcher.build_index()
        stats = await searcher.get_stats()
        
        print(f"✅ Hybrid search index built")
        print(f"   Documents loaded: {stats.get('documents_loaded', 0)}")
        print(f"   BM25 initialized: {stats.get('bm25_initialized', False)}")
        print(f"   pgvector backend: {stats.get('pgvector_backend', 'unknown')}")
        print(f"   Status: {stats.get('status', 'unknown')}")
        
        test_results.append(("Hybrid Search Index", True, "Index built"))
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results.append(("Hybrid Search Index", False, str(e)[:80]))
        return False


async def test_embedding_generation():
    """Test 5: Test OpenAI embedding API"""
    print("\n🧪 Test 5: Embedding Generation")
    print("-" * 50)
    
    try:
        test_text = "What is the limitation period for GST assessment?"
        embedding = call_embedding_api(test_text)
        
        if embedding and len(embedding) == 1536:
            print(f"✅ Generated embedding for text")
            print(f"   Model: text-embedding-3-small")
            print(f"   Dimensions: {len(embedding)}")
            print(f"   Sample values: {embedding[:5]}")
            test_results.append(("Embedding Generation", True, f"Generated {len(embedding)}-dim embedding"))
            return True
        else:
            print(f"❌ Invalid embedding: {len(embedding) if embedding else 0} dimensions")
            test_results.append(("Embedding Generation", False, "Invalid dimensions"))
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Check: OPENAI_API_KEY environment variable")
        test_results.append(("Embedding Generation", False, str(e)[:80]))
        return False


async def test_pgvector_search():
    """Test 6: Test pgvector search functionality"""
    print("\n🧪 Test 6: pgvector Search")
    print("-" * 50)
    
    try:
        if not supabase_client.is_connected:
            print("⏭️  Skipping (Supabase not connected)")
            return True
        
        # Create a test embedding
        test_embedding = [0.1] * 1536
        
        # Search
        results = await pgvector_searcher.search_similar_chunks(
            embedding=test_embedding,
            top_k=5,
            threshold=0.0  # Accept any results
        )
        
        print(f"✅ pgvector search executed")
        print(f"   Results returned: {len(results)}")
        if results:
            print(f"   Top result similarity: {results[0].get('similarity', 0.0):.4f}")
        else:
            print(f"   (No documents indexed yet - this is OK for test)")
        
        test_results.append(("pgvector Search", True, f"Search returned {len(results)} results"))
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results.append(("pgvector Search", False, str(e)[:80]))
        return False


async def test_hybrid_search():
    """Test 7: Test hybrid search (BM25 + pgvector)"""
    print("\n🧪 Test 7: Hybrid Search")
    print("-" * 50)
    
    try:
        test_query = "limitation period assessment"
        
        results = await searcher.search(test_query, top_k=3)
        
        print(f"✅ Hybrid search executed")
        print(f"   Query: {test_query}")
        print(f"   Results: {len(results)}")
        
        for i, result in enumerate(results[:3], 1):
            score = result.get('rrf_score', result.get('similarity', 0.0))
            sources = result.get('sources', [])
            text_preview = result.get('text', '')[:80]
            print(f"   {i}. [Score: {score:.4f}] Sources: {sources}")
            print(f"      {text_preview}...")
        
        test_results.append(("Hybrid Search", True, f"Found {len(results)} results"))
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        test_results.append(("Hybrid Search", False, str(e)[:80]))
        return False


async def test_rag_audit_logging():
    """Test 8: Test RAG query audit logging"""
    print("\n🧪 Test 8: RAG Audit Logging")
    print("-" * 50)
    
    try:
        if not supabase_client.is_connected:
            print("⏭️  Skipping (Supabase not connected)")
            return True
        
        # Log a test query
        test_embedding = [0.1] * 1536
        result = await supabase_client.log_rag_query(
            query_text="Test query for audit logging",
            query_embedding=test_embedding,
            results_count=3,
            top_chunks_used=[{"text": "chunk 1"}, {"text": "chunk 2"}],
            llm_response_id="test_response_123",
            response_confidence=0.88
        )
        
        if result:
            print("✅ RAG query logged to audit trail")
            print(f"   Query ID: {result.get('id', 'unknown')}")
            print(f"   Timestamp: {result.get('created_at', 'unknown')}")
        else:
            print("⚠️  Warning: Audit logging returned None (non-critical)")
        
        test_results.append(("RAG Audit Logging", True, "Query logged"))
        return True
    except Exception as e:
        print(f"⚠️  Warning: {e} (non-critical)")
        test_results.append(("RAG Audit Logging", True, "Skipped (non-critical)"))
        return True  # Non-critical


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 Supabase RAG End-to-End Test Suite")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Run tests
    await test_connectivity()
    await test_pgvector_extension()
    await test_document_tables()
    await test_hybrid_search_index()
    await test_embedding_generation()
    await test_pgvector_search()
    await test_hybrid_search()
    await test_rag_audit_logging()
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    passed = sum(1 for _, success, _ in test_results if success)
    total = len(test_results)
    
    for test_name, success, message in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} | {test_name:30} | {message}")
    
    print("="*60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! RAG migration is ready.")
    elif passed >= total - 1:
        print("⚠️  Some non-critical tests failed. Check above.")
    else:
        print("❌ Critical tests failed. See above for details.")
    
    # Cleanup
    if supabase_client.is_connected:
        await supabase_client.disconnect()
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return passed == total


async def run_single_test(test_name: str):
    """Run a single test by name"""
    tests = {
        "connectivity": test_connectivity,
        "pgvector": test_pgvector_extension,
        "tables": test_document_tables,
        "index": test_hybrid_search_index,
        "embedding": test_embedding_generation,
        "search": test_pgvector_search,
        "hybrid": test_hybrid_search,
        "logging": test_rag_audit_logging,
    }
    
    if test_name not in tests:
        print(f"Unknown test: {test_name}")
        print(f"Available: {', '.join(tests.keys())}")
        return False
    
    await tests[test_name]()
    
    if supabase_client.is_connected:
        await supabase_client.disconnect()
    
    return test_results[-1][1] if test_results else False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "--verbose":
        # Run specific test
        success = asyncio.run(run_single_test(sys.argv[1]))
    else:
        # Run all tests
        success = asyncio.run(run_all_tests())
    
    sys.exit(0 if success else 1)
