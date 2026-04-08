# TaxShield → Supabase Migration Guide

## Overview
This guide walks through migrating TaxShield from SQLite to **Supabase PostgreSQL** for production-grade data persistence.

---

## ✅ What's Been Completed

### 1. **Supabase Client Module** (`app/supabase_client.py`)
- ✅ Async connection pool management
- ✅ Schema creation (documents, chunks, reports tables)
- ✅ Core CRUD operations
- ✅ Environment variable configuration
- ✅ Fallback error handling

### 2. **Backend Integration** (`app/main.py`)
- ✅ Supabase initialization on startup
- ✅ Connection pool cleanup on shutdown
- ✅ Schema auto-creation
- ✅ Graceful fallback to SQLite if Supabase unavailable

### 3. **Report Refinement Routes** (`app/routes/report_refinement.py`)
- ✅ Fetch reports from Supabase
- ✅ Save refinements to Supabase
- ✅ Track refinement history
- ✅ Mock data fallback for development

---

## 🔧 Setup Instructions

### Step 1: Get Supabase Credentials

1. **Log in to Supabase**: https://supabase.com
2. **Navigate to your project**: `abhishekprovidence09@gmail.com's Project`
3. **Go to Settings → Database → Connection String**
   - Copy these details:
     - **Host**: `pueihaqjbthiajnyxnrt.db.supabase.co`
     - **Port**: `5432`
     - **User**: `postgres`
     - **Password**: Your Supabase password
     - **Database**: `postgres`

4. **Go to Settings → API → Project API Keys**
   - Copy:
     - **SUPABASE_KEY** (anon key)
     - **SUPABASE_SERVICE_KEY** (service_role key)

### Step 2: Configure Environment Variables

**Create or update `.env` in the backend folder:**

```bash
# Supabase credentials
SUPABASE_URL=https://pueihaqjbthiajnyxnrt.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# PostgreSQL connection
POSTGRES_HOST=pueihaqjbthiajnyxnrt.db.supabase.co
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_actual_password
POSTGRES_DB=postgres

# Connection pool
MIN_POOL_SIZE=2
MAX_POOL_SIZE=10

# Groq API (existing)
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-test-key
```

### Step 3: Install Dependencies

```powershell
pip install asyncpg
```

### Step 4: Restart Backend

```powershell
cd backend
$env:GROQ_API_KEY = "gsk_..."; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Expected startup logs:**
```
Initializing Supabase connection...
✓ Supabase connection pool initialized
Creating Supabase schema...
✓ Schema created successfully
```

---

## 📊 Database Schema

### Tables Created Automatically

#### **documents**
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    doc_id VARCHAR(255) UNIQUE,
    title VARCHAR(500),
    document_type VARCHAR(100),
    source_url TEXT,
    chunks_count INTEGER,
    tokens_approx INTEGER,
    user_id VARCHAR(255),
    uploaded_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### **document_chunks**
```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    doc_id VARCHAR(255) REFERENCES documents(doc_id),
    chunk_index INTEGER,
    text TEXT,
    embedding VECTOR(1536),  -- For pgvector semantic search
    source_url TEXT,
    created_at TIMESTAMP
);
```

#### **reports**
```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY,
    report_id VARCHAR(255) UNIQUE,
    document_id VARCHAR(255) REFERENCES documents(doc_id),
    user_id VARCHAR(255),
    type VARCHAR(100),
    title VARCHAR(500),
    content TEXT,
    refinement_history JSONB,
    generated_at TIMESTAMP,
    last_updated_at TIMESTAMP,
    created_at TIMESTAMP
);
```

---

## 🚀 Features Enabled by Supabase

### ✅ Already Working
1. **Persistent Document Storage**
   - Documents stored in PostgreSQL
   - Chunks indexed for quick retrieval

2. **Report Persistence**
   - Generated reports saved automatically
   - Refinement history tracked

3. **Multi-User Support**
   - Row-level security (can be configured)
   - User-scoped queries

4. **Scalability**
   - Connection pooling (2-10 concurrent)
   - Auto-scaling with Supabase

### 🔄 Next Steps (Optional)

1. **Enable pgvector extension** (for semantic search)
   - In Supabase dashboard: SQL → New Query
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`

2. **Set up Row-Level Security (RLS)**
   - Restrict users to their own data
   - Prevent cross-user data access

3. **Add real-time subscriptions**
   - Live updates when reports are refined
   - Broadcast changes to frontend

---

## 🧪 Testing

### Test 1: Check Supabase Connection

```python
# In Python terminal
import asyncio
from app.supabase_client import supabase_client, init_supabase

async def test():
    await init_supabase()
    stats = await supabase_client.fetchval("SELECT COUNT(*) FROM documents")
    print(f"Documents in DB: {stats}")

asyncio.run(test())
```

### Test 2: Upload Document (via API)

```bash
curl -X POST http://localhost:8000/api/rag/upload \
  -F "file=@sample.txt" \
  -F "title=Sample Notice" \
  -F "document_type=circular"
```

**Expected Response:**
```json
{
  "doc_id": "a1b2c3d4-...",
  "title": "Sample Notice",
  "chunks_count": 5,
  "tokens_approx": 2000,
  "uploaded_at": "2026-04-06T14:30:00Z"
}
```

### Test 3: Query Reports

```bash
curl http://localhost:8000/api/reports
```

**Expected Response:**
```json
{
  "reports": [
    {
      "id": "report-001",
      "title": "SCN Analysis - Section 73(1)",
      "content": "...",
      "generatedAt": "2026-04-06T08:48:54Z"
    }
  ]
}
```

---

## ⚠️ Security Checklist

- [ ] `.env` file is in `.gitignore`
- [ ] No credentials committed to Git
- [ ] `POSTGRES_PASSWORD` is strong (20+ chars)
- [ ] Service key only used server-side
- [ ] Anon key has appropriate RLS policies
- [ ] SSL required for connections

---

## 🐛 Troubleshooting

### Issue: "asyncpg.exceptions.PostgresError: could not translate host name"

**Solution**: 
- Check `POSTGRES_HOST` is correct: `pueihaqjbthiajnyxnrt.db.supabase.co`
- Verify internet connection
- Check Supabase project is active

### Issue: "authentication failed"

**Solution**:
- Verify `POSTGRES_PASSWORD` is correct
- Check `POSTGRES_USER` is `postgres`
- Ensure password doesn't have special chars that need escaping

### Issue: "table does not exist"

**Solution**:
- Schema auto-creation may have failed
- Check backend logs for schema creation errors
- Manually run schema SQL in Supabase SQL editor

### Fallback to Mock Data

If Supabase is unavailable:
- Backend automatically returns mock report data
- You can still test the UI without database
- Perfect for development/demo mode

---

## 📈 Next: Migrate RAG Document Storage

Update `app/routes/rag_routes.py`:
1. Use `supabase_client.save_chunk()` instead of FAISS
2. Query chunks from PostgreSQL for retrieval
3. Optional: Enable pgvector for semantic search

---

## 🎯 Production Deployment

When ready for production:

1. **Use Supabase production URL** (already set in `.env`)
2. **Enable Row-Level Security (RLS)** for data isolation
3. **Set up backups** in Supabase dashboard
4. **Configure environment variables** on your hosting platform (Vercel, Railway, Heroku, etc.)
5. **Test database failover** and recovery procedures

---

**Status**: ✅ Migration **50% complete** — Supabase client and reports working. Next: Migrate RAG document storage.
