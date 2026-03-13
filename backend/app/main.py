"""
TaxShield — FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import notices, chat, drafts, health
from app.middleware.error_handler import setup_error_handlers
from app.middleware.logging import setup_logging
from app.middleware.rate_limiter import setup_rate_limiting
from app.database import init_db
from app.logger import logger
from app.middleware.rate_limiter import _periodic_cleanup
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Import all models so Base.metadata knows about them
    import app.models.notice  # noqa: F401
    import app.models.draft   # noqa: F401
    import app.models.case    # noqa: F401

    # Startup: create DB tables
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    # Start background tasks
    cleanup_task = asyncio.create_task(_periodic_cleanup())

    yield

    # Shutdown: cancel background tasks
    cleanup_task.cancel()
    logger.info("Shutting down...")


app = FastAPI(title="TaxShield API", version="2.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Middleware
setup_error_handlers(app)
setup_logging(app)
setup_rate_limiting(app)

# Routes
app.include_router(health.router, tags=["Health"])
app.include_router(notices.router, prefix="/api", tags=["Notices"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(drafts.router, prefix="/api", tags=["Drafts"])
