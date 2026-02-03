import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    Global configuration for the PRISM Backend.
    Automatically loads values from environment variables and .env files.
    Prioritizes security and proper environment separation.
    """

    # --------------------------------------------------
    # Application Metadata
    # --------------------------------------------------
    APP_NAME: str = "PRISM AI Backend"
    APP_VERSION: str = "0.1.0-alpha"
    ENVIRONMENT: str = "development"

    # --------------------------------------------------
    # Server Configuration
    # --------------------------------------------------
    HOST: str = "0.0.0.0"  # Required for Render deployment
    PORT: int = int(os.getenv("PORT", "8000"))  # Render auto-assigns PORT
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8080,http://localhost:3000"
    )  # Add production frontend URL in production
    
    # --------------------------------------------------
    # Security Configuration
    # --------------------------------------------------
    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION"
    ENCRYPTION_KEY: str = "CHANGE_ME_32_CHARACTER_KEY_HERE"
    # Session configuration (server-side sessions)
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_EXPIRE_DAYS: int = 30
    AUTH_SINGLE_SESSION: bool = False  # If True, invalidate previous sessions on new login
    SESSION_COOKIE_SECURE: bool = False  # Default False for local HTTP; override to True in production
    SESSION_COOKIE_SAMESITE: str = "lax"  # "lax" for typical SPA, "strict" for extra security
    
    # --------------------------------------------------
    # AI/LLM Services (Groq Only)
    # --------------------------------------------------
    GROQ_API_KEY: str = ""                      # Groq LLM Key (Primary)
    GROQ_API_KEY_2: str = ""                    # Groq LLM Key #2 (Pool)
    GROQ_API_KEY_3: str = ""                    # Groq LLM Key #3 (Pool)
    GROQ_API_KEY_4: str = ""                    # Groq LLM Key #4 (Pool)
    GROQ_API_KEY_5: str = ""                    # Groq LLM Key #5 (Pool)
    GROQ_API_KEYS: str = ""                     # Comma-separated keys (alternative format)
    
    # --------------------------------------------------
    # Database Services
    # --------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0" # Redis (Short-term memory)
    PINECONE_API_KEY: str = ""                  # Pinecone (Long-term memory)
    PINECONE_INDEX_NAME: str = "prism-memory"   # Pinecone index name
    PINECONE_ENVIRONMENT: str = ""              # Pinecone environment (gcp-starter, us-east-1, etc.) - leave empty for serverless
    PINECONE_INDEX_TYPE: str = "serverless"     # "serverless" (cloud-native) or "pod" (legacy)
    MONGO_URI: str = "mongodb://localhost:27017/prismdb"# MongoDB (users, tasks, analytics)
    # Timezone for temporal grounding (e.g., Asia/Kolkata)
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")
    
    # --------------------------------------------------
    # Celery Configuration (Cloud-Native)
    # --------------------------------------------------
    # ☁️ CLOUD-NATIVE: Use rediss:// (with SSL) for production (Render, Upstash, AWS)
    # Fallback to redis:// for local development
    CELERY_BROKER_URL: str = ""  # If empty, uses REDIS_URL. Use rediss:// for cloud.
    CELERY_RESULT_BACKEND: str = ""  # If empty, uses REDIS_URL. Use rediss:// for cloud.

    # --------------------------------------------------
    # Email Service (SendGrid)
    # --------------------------------------------------
    SENDGRID_API_KEY: str = ""                  # SendGrid API Key
    SENDER_EMAIL: str = "dev@example.com"       # Verified sender email
    ENABLE_EMAIL_WORKER: bool = False           # Old Redis-based worker (disabled - using Celery now)

    # --------------------------------------------------
    # Email Limits & Retries
    # --------------------------------------------------
    MAX_DAILY_TASK_EMAILS: int = 10
    EMAIL_RETRY_DELAYS: list[int] = [10, 60, 300]  # seconds: 10s, 1m, 5m

    # --------------------------------------------------
    # Neo4j Graph Database
    # --------------------------------------------------
    NEO4J_URI: str = "neo4j://localhost:7687"   # neo4j+s://xxxx.databases.neo4j.io
    NEO4J_USER: str = "neo4j"                   # neo4j
    NEO4J_PASSWORD: str = ""                    # database password

    # --------------------------------------------------
    # Helper Properties
    # --------------------------------------------------
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def tzinfo(self):
        """Return tzinfo from configured timezone."""
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo(self.TIMEZONE)
        except Exception:
            import datetime as _dt
            return _dt.timezone.utc

    # --------------------------------------------------
    # Validation Methods
    # --------------------------------------------------
    def validate_critical_settings(self) -> List[str]:
        """Validate that critical settings are properly configured"""
        issues = []
        
        if self.is_production:
            if self.JWT_SECRET == "CHANGE_ME_IN_PRODUCTION":
                issues.append("JWT_SECRET must be changed in production")
            if self.ENCRYPTION_KEY == "CHANGE_ME_32_CHARACTER_KEY_HERE":
                issues.append("ENCRYPTION_KEY must be changed in production")
        
        if not self.GROQ_API_KEY:
            issues.append("GROQ_API_KEY is required")
            
        return issues

    # --------------------------------------------------
    # Pydantic Settings Config
    # --------------------------------------------------
    class Config:
        env_file = [".env.local", ".env"]  # Try .env.local first, then .env
        env_file_encoding = "utf-8"
        extra = "ignore"                   # Ignore unknown env vars
        case_sensitive = True              # Environment variables are case sensitive


# ------------------------------------------------------
# Export a Global Settings Instance
# ------------------------------------------------------
settings = Settings()
