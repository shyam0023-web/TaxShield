from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import notices, chat, drafts, health
from app.middleware.error_handler import setup_error_handlers
from app.middleware.logging import setup_logging
from app.middleware.rate_limiter import setup_rate_limiting

app = FastAPI(title="TaxShield API", version="2.0")

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
