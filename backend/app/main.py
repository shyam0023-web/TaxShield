"""
TaxShield — FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import notices, chat, drafts, health, auth, audit, verification, analytics, mfa, diff, kb_routes
try:
    from app.routes import rag_routes, report_refinement
except Exception:
    rag_routes = None
    report_refinement = None
from app.middleware.error_handler import setup_error_handlers
from app.middleware.logging import setup_logging
from app.middleware.rate_limiter import setup_rate_limiting
from app.database import init_db
from app.logger import logger
from app.middleware.rate_limiter import _periodic_cleanup
import asyncio

SCRAPE_INTERVAL_SECONDS = 7 * 24 * 60 * 60   # 7 days
RETENTION_INTERVAL_SECONDS = 24 * 60 * 60    # 24 hours


async def _weekly_cbic_scrape():
    """Background task: scrape CBIC for new circulars every 7 days."""
    await asyncio.sleep(30)  # Wait 30s after startup before first scrape
    while True:
        try:
            from app.tools.cbic_scraper import scrape_cbic_circulars
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                new_count = await scrape_cbic_circulars(db)
                logger.info(f"[Weekly Scraper] {new_count} new circulars staged")
        except Exception as e:
            logger.warning(f"[Weekly Scraper] Failed (non-fatal): {e}")
        await asyncio.sleep(SCRAPE_INTERVAL_SECONDS)


async def _daily_retention_cleanup():
    """DPDP Compliance: auto-delete notices older than 90 days, runs every 24h."""
    await asyncio.sleep(60)  # Wait 60s after startup before first run
    while True:
        try:
            from app.services.retention import run_retention_cleanup
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                result = await run_retention_cleanup(db)
                logger.info(f"[Retention] {result}")
        except Exception as e:
            logger.warning(f"[Retention] Failed (non-fatal): {e}")
        await asyncio.sleep(RETENTION_INTERVAL_SECONDS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Import all models so Base.metadata knows about them
    import app.models.notice  # noqa: F401
    import app.models.draft   # noqa: F401
    import app.models.case    # noqa: F401
    import app.models.user    # noqa: F401
    import app.models.audit_log  # noqa: F401
    import app.models.kb_staging   # noqa: F401

    # Startup: Initialize Supabase
    logger.info("Connecting to Supabase...")
    from app.supabase_client import supabase_client
    supabase_connected = await supabase_client.connect()
    if supabase_connected:
        logger.info("✅ Supabase PostgreSQL connected!")
    else:
        logger.warning("⚠️ Supabase unavailable — falling back to SQLite")

    # Startup: create DB tables
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    # Issue 2A: Clean up zombie notices from previous crashes
    try:
        from app.database import AsyncSessionLocal
        from sqlalchemy import select, update
        from app.models.notice import Notice
        from datetime import datetime, timedelta
        async with AsyncSessionLocal() as db:
            stale_cutoff = datetime.utcnow() - timedelta(minutes=5)
            result = await db.execute(
                update(Notice)
                .where(Notice.status == "processing", Notice.created_at < stale_cutoff)
                .values(status="error", error_message="Server restarted during processing. Please re-upload.")
            )
            if result.rowcount > 0:
                await db.commit()
                logger.info(f"Cleaned up {result.rowcount} stale 'processing' notices")
    except Exception as e:
        logger.warning(f"Stale notice cleanup failed (non-fatal): {e}")

    # Start background tasks
    cleanup_task = asyncio.create_task(_periodic_cleanup())
    scraper_task = asyncio.create_task(_weekly_cbic_scrape())
    retention_task = asyncio.create_task(_daily_retention_cleanup())

    yield

    # Shutdown: Disconnect from Supabase
    logger.info("Disconnecting from Supabase...")
    await supabase_client.disconnect()

    # Shutdown: cancel background tasks
    cleanup_task.cancel()
    scraper_task.cancel()
    retention_task.cancel()

    # Close Redis connection pool
    from app.redis_client import close_redis
    await close_redis()

    logger.info("Shutting down...")


app = FastAPI(title="TaxShield API", version="2.0", lifespan=lifespan)

# Middleware (order matters — CORS must be LAST so it wraps outermost)
setup_error_handlers(app)
setup_logging(app)
setup_rate_limiting(app)

# CORS — must be added last so headers are on ALL responses including 401/500
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "https://taxshield-frontendd.onrender.com",
        "https://taxshield.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(notices.router, prefix="/api", tags=["Notices"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(drafts.router, prefix="/api", tags=["Drafts"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(audit.router, prefix="/api", tags=["Audit"])
app.include_router(verification.router, prefix="/api", tags=["Email Verification"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(mfa.router, prefix="/api", tags=["MFA"])
app.include_router(diff.router, prefix="/api", tags=["Draft Diff"])
app.include_router(kb_routes.router, prefix="/api", tags=["KB Review"])
if rag_routes:
    app.include_router(rag_routes.router, tags=["RAG"])
if report_refinement:
    app.include_router(report_refinement.router, prefix="/api", tags=["Report Refinement"])
