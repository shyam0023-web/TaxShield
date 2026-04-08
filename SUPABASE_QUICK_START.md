# 🚀 Supabase Quick Start - 5 Minutes

## Step 1: Get Credentials (2 min)
```
https://supabase.com
→ Your Project
→ Settings → Database
Copy: Host, User, Password, Port
→ Settings → API → Copy both keys
```

## Step 2: Create `.env` (1 min)
```bash
cd backend
copy .env.supabase.example .env
# Edit .env with your credentials from Step 1
```

## Step 3: Install & Run (2 min)
```powershell
pip install asyncpg
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Step 4: Verify ✅
```bash
curl http://localhost:8000/api/reports
# Should return: {"reports": []}
```

---

## .env Template
```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
POSTGRES_HOST=YOUR_PROJECT.db.supabase.co
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=YOUR_PASSWORD
POSTGRES_DB=postgres
```

---

## Expected Backend Logs
```
✓ Supabase connection pool initialized
✓ Schema created successfully
✓ Application startup complete
```

---

## Test Endpoints
- `GET /api/reports` → List reports from Supabase
- `POST /api/reports/refine` → Save refinement to Supabase
- `GET /api/documents` → List documents

---

**Done!** 🎉 Your app is now using Supabase PostgreSQL for persistent storage.
