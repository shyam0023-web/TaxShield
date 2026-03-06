from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    
    # Database (Supabase)
    DATABASE_URL: str = ""
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Langfuse
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    
    # Cohere (reranker)
    COHERE_API_KEY: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
