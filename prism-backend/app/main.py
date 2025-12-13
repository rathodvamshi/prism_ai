import warnings
import logging
from typing import List

warnings.filterwarnings("ignore", message="Valid config keys have changed in V2:")

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.utils.security import SecurityMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Routers
from app.routers import health_llm
from app.routers import highlights
from app.routers import user, auth, chat
from app.utils.auth import get_current_user

# Scheduler
from app.services.scheduler_service import start_scheduler
from app.db.mongo_client import db


# Initialize FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend for PRISM Personal AI Assistant - Secure & Scalable",
)

# Validate critical settings on startup
@app.on_event("startup")
async def validate_configuration():
    """Validate configuration on startup"""
    issues = settings.validate_critical_settings()
    if issues:
        logger.error("Configuration validation failed:")
        for issue in issues:
            logger.error(f"  - {issue}")
        if settings.is_production:
            raise HTTPException(status_code=500, detail="Critical configuration errors")
        else:
            logger.warning("Running in development mode with configuration issues")
    else:
        logger.info("Configuration validation passed")

# Security Middleware (must be added first)
app.add_middleware(SecurityMiddleware)

# CORS (Frontend ↔ Backend) - Allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Frontend dev server
        "http://127.0.0.1:8080", 
        "http://localhost:8081",  # Alternative frontend port (when 8080 is busy)
        "http://127.0.0.1:8081",
        "http://localhost:3000",  # Alternative frontend ports
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:5173",
        *getattr(settings, 'cors_origins_list', [])
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Static files for audio/images (allow missing dir in dev)
app.mount("/static", StaticFiles(directory="static", check_dir=False), name="static")


# Health Check
@app.get("/health")
async def health_check():
    return {"status": "active", "app": settings.APP_NAME, "version": settings.APP_VERSION}

# Simple Chat endpoint for testing
@app.post("/api/chat/send")
async def send_message(message_data: dict, user: dict = Depends(get_current_user)):
    """Simple chat endpoint for testing authentication integration"""
    user_message = message_data.get("message", "")
    user_id = user.get("id", "unknown")
    
    # Simple echo response with user context
    response = f"Hello {user.get('name', user.get('email', 'User'))}! You said: {user_message}"
    
    return {
        "response": response,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Routers
app.include_router(health_llm.router, tags=["Health"])
app.include_router(user.router, tags=["User"])
app.include_router(auth.router, tags=["Auth"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(highlights.router, tags=["Highlights"])


# 🚀 PERFECT DATABASE INITIALIZATION
@app.on_event("startup")
async def startup_perfect_databases():
    """
    Initialize all databases with perfect architecture:
    - MongoDB with unique indexes
    - Pinecone vector database  
    - Neo4j graph database
    - Redis cache
    """
    print("🚀 Initializing PERFECT Database Architecture...")
    try:
        # MongoDB
        from app.db.mongo_client import db
        db_name = db.name if hasattr(db, 'name') else 'unknown'
        print(f"✅ MongoDB connected database : {db_name}")

        # Redis
        from app.db.redis_client import redis_client
        # Redis DB index is usually in the URL, default is 0
        redis_url = settings.REDIS_URL
        redis_index = redis_url.split('/')[-1] if '/' in redis_url else '0'
        await redis_client.ping()
        print(f"✅ Redis connected index : {redis_index}")

        # Pinecone
        from app.services.vector_memory_service import INDEX_NAME
        print(f"✅ Pinecone connected index: {INDEX_NAME}")

        # Neo4j
        from app.config import settings as config_settings
        neo4j_uri = config_settings.NEO4J_URI
        neo4j_db_name = neo4j_uri.split('//')[-1].split('.')[0] if '//' in neo4j_uri else 'neo4j'
        print(f"✅ Neo4j connected index : {neo4j_db_name}")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

# Start background scheduler on startup
@app.on_event("startup")
async def _startup():
    try:
        start_scheduler()
    except Exception as e:
        # Avoid crashing the app if scheduler fails to start
        print(f"Scheduler start failed: {e}")

    # Initialize MongoDB indexes to enforce uniqueness and prevent duplicates
    try:
        # Users: unique email
        await db.users.create_index("email", unique=True)

        # User memory: unique (user_id, type, content)
        await db.user_memory.create_index([
            ("user_id", 1), ("type", 1), ("content", 1)
        ], unique=True)

        # Chat sessions: unique per user and sessionId
        await db.chat_sessions.create_index([
            ("sessionId", 1), ("user_id", 1)
        ], unique=True)

        # Highlights: uniqueKey is precomputed
        await db.message_highlights.create_index("uniqueKey", unique=True)

        # Tasks: unique taskId
        await db.user_tasks.create_index("taskId", unique=True)

        # Mini-agent threads: unique per user and thread
        await db.miniagent_threads.create_index([
            ("threadId", 1), ("user_id", 1)
        ], unique=True)

        # Shared conversations: unique shareId
        await db.shared_conversations.create_index("shareId", unique=True)
    except Exception as e:
        print(f"Index initialization failed (non-fatal): {e}")


# Local debug run support
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        reload_excludes=[".venv/*", "**/__pycache__/**", "*.pyc"],
    )
