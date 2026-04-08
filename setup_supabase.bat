@echo off
REM ═══════════════════════════════════════════════════════════════════════════
REM TaxShield → Supabase Setup Script
REM Run this to initialize Supabase for TaxShield
REM ═══════════════════════════════════════════════════════════════════════════

echo.
echo 🚀 TaxShield Supabase Setup
echo ═══════════════════════════════════════════════════════════════════════════
echo.

REM Check if .env exists
if not exist backend\.env (
    echo ⚠️  .env file not found in backend folder
    echo.
    echo 📋 Steps to configure:
    echo 1. Copy backend\.env.supabase.example to backend\.env
    echo 2. Get credentials from Supabase dashboard:
    echo    - https://supabase.com → Your Project
    echo    - Settings → Database → Connection String
    echo    - Settings → API → Project API Keys
    echo 3. Update .env with your credentials
    echo 4. Run this script again
    echo.
    pause
    exit /b 1
)

echo ✓ .env file found
echo.

REM Install asyncpg
echo 📦 Installing asyncpg...
pip install asyncpg -q
if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to install asyncpg
    pause
    exit /b 1
)
echo ✓ asyncpg installed

echo.
echo ✅ Setup complete!
echo.
echo 🚀 Next steps:
echo 1. Start backend with Supabase:
echo    cd backend
echo    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
echo.
echo 2. Check logs for:
echo    ✓ Supabase connection pool initialized
echo    ✓ Schema created successfully
echo.
echo 3. Start frontend:
echo    cd frontend
echo    npm run dev
echo.
echo 4. Open: http://localhost:3000/reports
echo.
echo 📚 Documentation: SUPABASE_MIGRATION.md
echo.
pause
