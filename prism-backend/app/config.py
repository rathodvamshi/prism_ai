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
    HOST: str = "localhost"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:8080,http://localhost:3000"
    
    # --------------------------------------------------
    # Security Configuration
    # --------------------------------------------------
    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION"
    ENCRYPTION_KEY: str = "CHANGE_ME_32_CHARACTER_KEY_HERE"
    
    # --------------------------------------------------
    # AI/LLM Services
    # --------------------------------------------------
    GROQ_API_KEY: str = ""                      # Groq LLM Key
    OPENAI_API_KEY: str = ""                    # OpenAI API Key (optional)
    
    # --------------------------------------------------
    # Database Services
    # --------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0" # Redis (Short-term memory)
    PINECONE_API_KEY: str = ""                  # Pinecone (Long-term memory)
    MONGO_URI: str = "mongodb://localhost:27017/prism"# MongoDB (users, tasks, analytics)

    # --------------------------------------------------
    # Email Service (SendGrid)
    # --------------------------------------------------
    SENDGRID_API_KEY: str = ""                  # SendGrid API Key
    SENDER_EMAIL: str = "dev@example.com"       # Verified sender email

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
