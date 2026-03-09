from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from app.config import settings
from app.logger import logger
from app.gemini_client import gemini_client
from app.groq_client import groq_client


# Create main router
router = APIRouter()

@router.get("/status", response_model=Dict[str, Any])
async def get_system_status():
    """Get system status and configuration"""
    try:
        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "gemini": {
                    "configured": bool(settings.GEMINI_API_KEY),
                    "model_info": gemini_client.get_model_info()
                },
                "groq": {
                    "configured": bool(settings.GROQ_API_KEY),
                    "model_info": groq_client.get_model_info(),
                    "available_models": groq_client.get_available_models()
                },
                "database": {
                    "url": settings.DATABASE_URL,
                    "type": "sqlite" if "sqlite" in settings.DATABASE_URL else "other"
                },
                "redis": {
                    "url": settings.REDIS_URL,
                    "configured": bool(settings.REDIS_URL)
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")


@router.get("/models", response_model=Dict[str, Any])
async def get_available_models():
    """Get available AI models"""
    try:
        return {
            "gemini": {
                "available": bool(settings.GEMINI_API_KEY),
                "models": ["gemini-1.5-flash", "gemini-1.5-pro"],
                "current": getattr(gemini_client.model, 'model_name', 'unknown') if gemini_client.model else None
            },
            "groq": {
                "available": bool(settings.GROQ_API_KEY),
                "models": groq_client.get_available_models(),
                "default": groq_client.default_model
            }
        }
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available models")


@router.post("/test/gemini", response_model=Dict[str, Any])
async def test_gemini(prompt: str = "Hello, please respond with a brief greeting."):
    """Test Gemini API connectivity"""
    try:
        if not settings.GEMINI_API_KEY:
            raise HTTPException(status_code=400, detail="Gemini API key not configured")
        
        response = await gemini_client.generate_response(prompt)
        
        return {
            "status": "success",
            "prompt": prompt,
            "response": response,
            "model_info": gemini_client.get_model_info()
        }
    except Exception as e:
        logger.error(f"Error testing Gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini test failed: {str(e)}")


@router.post("/test/groq", response_model=Dict[str, Any])
async def test_groq(prompt: str = "Hello, please respond with a brief greeting."):
    """Test Groq API connectivity"""
    try:
        if not settings.GROQ_API_KEY:
            raise HTTPException(status_code=400, detail="Groq API key not configured")
        
        response = await groq_client.generate_response(prompt)
        
        return {
            "status": "success",
            "prompt": prompt,
            "response": response,
            "model_info": groq_client.get_model_info()
        }
    except Exception as e:
        logger.error(f"Error testing Groq: {e}")
        raise HTTPException(status_code=500, detail=f"Groq test failed: {str(e)}")


@router.post("/compare", response_model=Dict[str, Any])
async def compare_models(
    prompt: str,
    gemini_model: Optional[str] = None,
    groq_model: Optional[str] = None
):
    """Compare responses from both Gemini and Groq models"""
    try:
        tasks = []
        
        if settings.GEMINI_API_KEY:
            tasks.append({
                "name": "gemini",
                "task": gemini_client.generate_response(prompt, model=gemini_model)
            })
        
        if settings.GROQ_API_KEY:
            tasks.append({
                "name": "groq", 
                "task": groq_client.generate_response(prompt, model=groq_model)
            })
        
        if not tasks:
            raise HTTPException(status_code=400, detail="No AI models configured")
        
        # Execute tasks concurrently
        results = {}
        for task_info in tasks:
            try:
                response = await task_info["task"]
                results[task_info["name"]] = {
                    "status": "success",
                    "response": response
                }
            except Exception as e:
                results[task_info["name"]] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "prompt": prompt,
            "timestamp": datetime.utcnow().isoformat(),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error comparing models: {e}")
        raise HTTPException(status_code=500, detail=f"Model comparison failed: {str(e)}")


@router.post("/generate/structured", response_model=Dict[str, Any])
async def generate_structured_response(
    prompt: str,
    schema: Dict[str, Any],
    provider: str = "gemini",
    model: Optional[str] = None
):
    """Generate structured response using specified provider"""
    try:
        if provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise HTTPException(status_code=400, detail="Gemini API key not configured")
            
            response = await gemini_client.generate_structured_response(prompt, schema)
            
        elif provider == "groq":
            if not settings.GROQ_API_KEY:
                raise HTTPException(status_code=400, detail="Groq API key not configured")
            
            response = await groq_client.generate_structured_response(prompt, schema, model=model)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
        
        return {
            "status": "success",
            "provider": provider,
            "prompt": prompt,
            "schema": schema,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating structured response: {e}")
        raise HTTPException(status_code=500, detail=f"Structured generation failed: {str(e)}")


@router.get("/config", response_model=Dict[str, Any])
async def get_public_config():
    """Get public configuration (no sensitive data)"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "features": {
            "gemini_enabled": bool(settings.GEMINI_API_KEY),
            "groq_enabled": bool(settings.GROQ_API_KEY),
            "cohere_enabled": bool(settings.COHERE_API_KEY),
            "langfuse_enabled": bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY)
        }
    }


@router.post("/chat/stream")
async def stream_chat(
    prompt: str,
    provider: str = "groq",
    system_message: Optional[str] = None,
    model: Optional[str] = None
):
    """Stream chat response"""
    try:
        if provider == "groq":
            if not settings.GROQ_API_KEY:
                raise HTTPException(status_code=400, detail="Groq API key not configured")
            
            return JSONResponse(
                content={
                    "stream": groq_client.stream_response(
                        prompt=prompt,
                        system_message=system_message,
                        model=model
                    )
                }
            )
        else:
            raise HTTPException(status_code=400, detail=f"Streaming not supported for provider: {provider}")
            
    except Exception as e:
        logger.error(f"Error in stream chat: {e}")
        raise HTTPException(status_code=500, detail=f"Stream chat failed: {str(e)}")


# Health check endpoint
@router.get("/health", response_model=Dict[str, str])
async def health_check():
    """Simple health check"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Include router in main app
def setup_routes(app):
    """Setup all routes in the FastAPI app"""
    app.include_router(router, prefix="/api/v1", tags=["System"])
    logger.info("System routes configured")
