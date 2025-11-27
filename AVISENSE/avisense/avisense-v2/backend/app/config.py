from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # Model
    MODEL_PATH: str = "./models"
    MODEL_ARTIFACT_URL: str | None = None
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://*.vercel.app"
    ]
    
    # Security
    JWT_SECRET: str | None = None
    RATE_LIMIT_PER_MINUTE: int = 10
    
    # Monitoring
    SENTRY_DSN: str | None = None
    ENABLE_METRICS: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
