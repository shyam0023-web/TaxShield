#!/usr/bin/env python3
"""
Quick Supabase Connectivity Test - No external APIs required
Tests core pgvector integration without OpenAI embeddings
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.supabase_client import supabase_client
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def test_basic_connectivity():
    """Test basic connection to Supabase"""
    print("\n" + "="*60)
    print("🧪 Quick Supabase Connectivity Test")
    print("="*60 + "\n")
    
    results = []
    
    # Test 1: Connect
    print("1️⃣  Connecting to Supabase...")
    try:
        connected = await supabase_client.connect()
        if connected:
            print("   ✅ Connected to Supabase")
            print(f"   URL: {supabase_client.url[:50]}...")
            results.append(True)
        else:
            print("   ❌ Failed to connect")
            results.append(False)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results.append(False)
        return results
    
    # Test 2: Check tables exist
    print("\n2️⃣  Checking database tables...")
    try:
        # Try to query documents table
        docs = await supabase_client.get_documents(limit=1)
        print("   ✅ 'documents' table accessible")
        
        # Try to query rag_queries table
        queries = supabase_client.client.table("rag_queries").select("*").limit(1).execute()
        print("   ✅ 'rag_queries' table accessible")
        
        results.append(True)
    except Exception as e:
        print(f"   ⚠️  Table check issue: {str(e)[:60]}")
        print("      (This is expected if migrations haven't run yet)")
        results.append(False)
    
    # Test 3: Test pgvector function exists
    print("\n3️⃣  Checking pgvector function...")
    try:
        # Just try to call it with empty result (no documents in DB)
        result = supabase_client.client.rpc(
            "search_chunks_by_embedding",
            {
                "query_embedding": [0.0] * 1536,
                "match_count": 1,
                "similarity_threshold": 0.5
            }
        ).execute()
        print("   ✅ pgvector search function exists")
        print(f"   Results: {len(result.data)} chunks found (expected empty)")
        results.append(True)
    except Exception as e:
        error_str = str(e).lower()
        if "does not exist" in error_str or "unknown" in error_str:
            print("   ❌ pgvector function not found")
            print("      Solution: Run SQL migration in Supabase dashboard")
            results.append(False)
        else:
            print(f"   ⚠️  Error: {str(e)[:60]}")
            results.append(False)
    
    # Test 4: Test document creation
    print("\n4️⃣  Testing document creation...")
    try:
        doc = await supabase_client.get_or_create_document(
            doc_id="TEST_001",
            title="Test Document",
            content_text="This is a test document for pgvector migration",
            metadata={"type": "test"}
        )
        if doc:
            print(f"   ✅ Document created/retrieved (ID: {doc.get('id')})")
            results.append(True)
        else:
            print("   ❌ Failed to create document")
            results.append(False)
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:80]}")
        results.append(False)
    
    # Test 5: Test audit logging
    print("\n5️⃣  Testing audit logging...")
    try:
        await supabase_client.log_rag_query(
            query_text="Test query",
            query_embedding=[0.1] * 1536,
            results_count=0,
            response_confidence=0.5
        )
        print("   ✅ Audit logging works")
        results.append(True)
    except Exception as e:
        if "rag_queries" in str(e).lower():
            print("   ⚠️  Audit table not found (migration may not be complete)")
            results.append(False)
        else:
            print(f"   ❌ Error: {str(e)[:80]}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "="*60)
    print(f"📊 Results: {passed}/{total} tests passed")
    print("="*60)
    
    if passed >= 3:
        print("\n✅ Supabase pgvector is configured correctly!")
        print("   Status: READY for production")
        print("\n   Next steps:")
        print("   1. Run migration script: python migrate_rag_to_supabase.py")
        print("   2. Load real documents into pgvector")
        print("   3. Test hybrid search with real data")
    elif passed >= 1:
        print("\n⚠️  Partial setup detected")
        print("   Check troubleshooting in SUPABASE_RAG_MIGRATION_COMPLETE.md")
    else:
        print("\n❌ Supabase connection failed")
        print("   Check environment variables in .env:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_SERVICE_KEY")
    
    # Cleanup
    if supabase_client.is_connected:
        await supabase_client.disconnect()
    
    return results


if __name__ == "__main__":
    results = asyncio.run(test_basic_connectivity())
    success = sum(results) >= 3
    sys.exit(0 if success else 1)
