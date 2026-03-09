from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM Keys
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    
    # Database
    DATABASE_URL: str = "sqlite:///./taxshield.db"  # SQLite for now, Supabase later
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Cohere (reranker)
    COHERE_API_KEY: str = ""
    
    # Langfuse (observability)
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    
    # App
    APP_NAME: str = "TaxShield"
    APP_VERSION: str = "2.0"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
