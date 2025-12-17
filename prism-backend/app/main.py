import warnings
import logging
from typing import List, Optional
from contextlib import asynccontextmanager

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
from app.routers import user, auth, chat, tasks
from app.utils.auth import get_current_user_from_session

# Scheduler
from app.services.scheduler_service import start_scheduler
from app.db.mongo_client import db, connect_to_mongo, close_mongo
# ☁️ CLOUD-NATIVE: Old email_worker.py removed - using Celery now
# Email tasks are handled by separate Celery worker process
import asyncio


# Global worker task handle
worker_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    🔌 Application Lifecycle with Connection Pooling.
    
    Startup:
    - Connect to MongoDB
    - Validate connection pools
    - Start background workers
    
    Shutdown:
    - Stop workers gracefully
    - Close all connections
    - Release connection pools
    """
    global worker_task
    
    # Startup
    print("🚀 Connecting to MongoDB...")
    await connect_to_mongo()
    
    # 🔐 Initialize User Resolution Service (CRITICAL for ONE EMAIL = ONE USER)
    print("🔐 Initializing User Resolution Service...")
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.config import settings as app_settings
        from app.services.user_resolution_service import initialize_user_resolution_service
        from app.db.mongo_client import _sanitize_mongo_uri
        
        # Sanitize MongoDB URI to handle special characters in username/password
        sanitized_uri = _sanitize_mongo_uri(app_settings.MONGO_URI)
        mongo_client = AsyncIOMotorClient(sanitized_uri)
        user_resolution_service = initialize_user_resolution_service(mongo_client)
        
        # Enforce unique email index
        await user_resolution_service.ensure_unique_index()
        
        # Validate no duplicates exist
        is_valid, duplicates = await user_resolution_service.validate_no_duplicates()
        if not is_valid:
            logger.error(f"🚨 DUPLICATE USERS FOUND: {len(duplicates)} emails with duplicates")
            logger.error("⚠️ System will prevent NEW duplicates, but existing ones should be cleaned")
        else:
            logger.info("✅ User Resolution Service: No duplicates found")
        
        logger.info("✅ User Resolution Service initialized and enforced")
    except Exception as e:
        logger.error(f"❌ User Resolution Service initialization failed: {e}")
        logger.error("⚠️ System will run but user identity enforcement is DISABLED")
    
    # �🚀 Part 17: Backend warmup on reconnect
    print("🔥 Warming up connections...")
    
    # 1. Warm Redis connection
    try:
        from app.db.redis_client import redis_client
        await redis_client.ping()
        logger.info("✅ Redis warmed up")
    except Exception as e:
        logger.warning(f"⚠️ Redis warmup failed: {e}")
    
    # 2. Warm MongoDB connection
    try:
        from app.db.mongo_client import db
        await db.command('ping')
        logger.info("✅ MongoDB warmed up")
    except Exception as e:
        logger.warning(f"⚠️ MongoDB warmup failed: {e}")
    
    # 3. Warm Neo4j connection (optional)
    try:
        from app.db.neo4j_client import neo4j_client
        if neo4j_client.is_available:
            await neo4j_client.verify_connectivity()
            logger.info("✅ Neo4j warmed up")
    except Exception as e:
        logger.warning(f"⚠️ Neo4j warmup failed (non-critical): {e}")
    
    # 4. Schedule ONLY nearest task (not all tasks)
    try:
        from app.services.scheduler_service import schedule_next_task
        await schedule_next_task()  # Schedules only the next pending task
        logger.info("✅ Nearest task scheduled")
    except Exception as e:
        logger.warning(f"⚠️ Task scheduler warmup failed: {e}")
    
    print("🔌 Validating connection pools...")
    from app.db.connection_pool import validate_all_pools
    pools_ok = await validate_all_pools()
    if not pools_ok:
        logger.warning("⚠️ Some connection pools failed validation")
    
    # ☁️ CLOUD-NATIVE: Email worker is now handled by separate Celery process
    # No need to start old Redis-based worker - Celery handles all background tasks
    print("ℹ️ Email tasks handled by Celery worker (separate process)")
    worker_task = None
    
    try:
        yield
    finally:
        # Shutdown
        if worker_task:
            print("🛑 Stopping Worker safely...")
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                print("✅ Worker shut down successfully.")
        
        print("🛑 Closing all connections...")
        from app.db.connection_pool import cleanup_all_connections
        await cleanup_all_connections()
        
        print("🛑 Closing MongoDB...")
        await close_mongo()


# Initialize FastAPI with lifespan handler
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend for PRISM Personal AI Assistant - Secure & Scalable",
    lifespan=lifespan,
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

# 🚀 Part 19: Structured Logging Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with user_id, intent, latency"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract user info if authenticated
        user_id = "anonymous"
        try:
            # Try to get user from auth header (if present)
            auth_header = request.headers.get("authorization", "")
            if auth_header:
                # User will be set by auth dependency
                # For middleware, just log that it's authenticated
                user_id = "authenticated"
        except:
            pass
        
        # Extract intent from path
        path = request.url.path
        intent = path.split("/")[-1] if path else "unknown"
        
        try:
            response = await call_next(request)
            latency_ms = (time.time() - start_time) * 1000
            
            # Log successful request
            logger.info(
                f"📊 REQUEST | "
                f"path={path} method={request.method} "
                f"user={user_id} intent={intent} "
                f"latency_ms={latency_ms:.2f} status={response.status_code}"
            )
            
            return response
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            # Log failed request
            logger.error(
                f"⚠️ REQUEST_ERROR | "
                f"path={path} method={request.method} "
                f"user={user_id} intent={intent} "
                f"latency_ms={latency_ms:.2f} error={type(e).__name__}"
            )
            raise

# Security Middleware (must be added first)
app.add_middleware(SecurityMiddleware)

# 🚀 Part 19: Structured Logging (added after security)
app.add_middleware(StructuredLoggingMiddleware)

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
    """Basic health check endpoint"""
    return {"status": "active", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# Celery Health Check
@app.get("/health/celery")
async def celery_health_check():
    """Check Celery worker status and configuration"""
    try:
        from app.core.celery_app import verify_celery_setup, CELERY_AVAILABLE, celery_app
        
        # Use verification function for comprehensive check
        verification = verify_celery_setup()
        
        if not CELERY_AVAILABLE or celery_app is None:
            return {
                "status": "unavailable",
                **verification,
                "message": "Celery is not installed. Install with: pip install 'celery[redis]>=5.3.0'",
                "worker_running": False
            }
        
        # Try to inspect active workers for detailed status
        try:
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            scheduled_tasks = inspect.scheduled()
            reserved_tasks = inspect.reserved()
            stats = inspect.stats()
            
            worker_count = len(active_workers) if active_workers else 0
            scheduled_count = sum(len(tasks) for tasks in scheduled_tasks.values()) if scheduled_tasks else 0
            reserved_count = sum(len(tasks) for tasks in reserved_tasks.values()) if reserved_tasks else 0
            
            # Determine overall status
            if worker_count > 0 and verification["tasks_registered"]:
                status = "healthy"
            elif worker_count == 0:
                status = "no_workers"
            elif not verification["tasks_registered"]:
                status = "tasks_not_registered"
            else:
                status = "warning"
            
            return {
                "status": status,
                **verification,
                "worker_running": worker_count > 0,
                "active_workers": worker_count,
                "scheduled_tasks": scheduled_count,
                "reserved_tasks": reserved_count,
                "broker_url": str(celery_app.conf.broker_url)[:50] + "..." if hasattr(celery_app.conf, 'broker_url') else "unknown",
                "timezone": celery_app.conf.timezone,
                "utc_enabled": celery_app.conf.enable_utc,
                "worker_stats": stats
            }
        except Exception as inspect_error:
            return {
                "status": "error",
                **verification,
                "celery_installed": True,
                "worker_running": False,
                "error": str(inspect_error),
                "message": "Celery is installed but cannot connect to workers. Make sure Celery worker is running."
            }
    except Exception as e:
        return {
            "status": "error",
            "celery_installed": False,
            "error": str(e),
            "message": "Failed to check Celery status"
        }


# 🚀 Part 16: Frontend Reconnect Endpoint (OPTIMIZED)
@app.post("/api/reconnect")
async def reconnect(user: dict = Depends(get_current_user_from_session)):
    """
    Efficient reconnection endpoint for frontend.
    
    Only fetches:
    - Active session ID (not full history)
    - Latest 10 messages
    - Pending tasks only
    
    NOT fetched:
    - Full message history
    - Completed tasks
    - Archived sessions
    """
    from app.db.mongo_client import sessions_collection, tasks_collection
    from bson import ObjectId
    
    user_id = ObjectId(user.user_id)
    
    # 1. Get only ACTIVE session (not all sessions)
    active_session = await sessions_collection.find_one(
        {"userId": user_id, "isActive": True},
        {"sessionId": 1, "updatedAt": 1, "messages": {"$slice": -10}}  # Only last 10 messages
    )
    
    # 2. Get only PENDING tasks (not completed/cancelled)
    pending_tasks = await tasks_collection.find(
        {"userId": user_id, "status": "pending"},
        {"description": 1, "due_date": 1, "status": 1}  # Only essential fields
    ).limit(20).to_list(20)
    
    # Format response
    return {
        "user": {
            "id": str(user_id),
            "email": user.email,
            "name": user.name
        },
        "activeSession": {
            "sessionId": active_session.get("sessionId") if active_session else None,
            "messageCount": len(active_session.get("messages", [])) if active_session else 0,
            "recentMessages": active_session.get("messages", [])[-10:] if active_session else []
        },
        "pendingTasks": [
            {
                "id": str(t["_id"]),
                "description": t.get("description"),
                "dueDate": t.get("due_date"),
                "status": t.get("status")
            }
            for t in pending_tasks
        ],
        "reconnectedAt": datetime.now(timezone.utc).isoformat()
    }

# Simple Chat endpoint for testing
@app.post("/api/chat/send")
async def send_message(message_data: dict, user: dict = Depends(get_current_user_from_session)):
    """Simple chat endpoint for testing authentication integration"""
    user_message = message_data.get("message", "")
    user_id = user.user_id or "unknown"
    
    # Simple echo response with user context
    display_name = user.name or user.email or "User"
    response = f"Hello {display_name}! You said: {user_message}"
    
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
app.include_router(tasks.router, tags=["Tasks"])
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

        # Neo4j - Verify connectivity
        from app.db.neo4j_client import neo4j_client
        from app.config import settings as config_settings
        neo4j_uri = config_settings.NEO4J_URI
        neo4j_db_name = neo4j_uri.split('//')[-1].split('.')[0] if '//' in neo4j_uri else 'neo4j'
        
        if neo4j_client.is_available:
            connection_ok = await neo4j_client.verify_connectivity()
            if connection_ok:
                print(f"✅ Neo4j connected index : {neo4j_db_name}")
            else:
                print(f"⚠️ Neo4j driver created but connection failed")
                print(f"💡 Run: python test_neo4j_connection.py for diagnostics")
        else:
            print(f"⚠️ Neo4j not configured (operations will be skipped)")
            
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

# 🚀 PRODUCTION: Scheduler removed from API server
# ❌ Email sending now handled by separate email_worker.py process
# Run: python email_worker.py in separate terminal

@app.on_event("startup")
async def _startup():
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



# Security Middleware (must be added first)

app.add_middleware(SecurityMiddleware)



# 🚀 Part 19: Structured Logging (added after security)

app.add_middleware(StructuredLoggingMiddleware)



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





# 🚀 Part 16: Frontend Reconnect Endpoint (OPTIMIZED)

@app.post("/api/reconnect")
async def reconnect(user: dict = Depends(get_current_user_from_session)):

    """

    Efficient reconnection endpoint for frontend.

    

    Only fetches:

    - Active session ID (not full history)

    - Latest 10 messages

    - Pending tasks only

    

    NOT fetched:

    - Full message history

    - Completed tasks

    - Archived sessions

    """

    from app.db.mongo_client import sessions_collection, tasks_collection

    from bson import ObjectId

    

    user_id = ObjectId(user.user_id)

    

    # 1. Get only ACTIVE session (not all sessions)

    active_session = await sessions_collection.find_one(

        {"userId": user_id, "isActive": True},

        {"sessionId": 1, "updatedAt": 1, "messages": {"$slice": -10}}  # Only last 10 messages

    )

    

    # 2. Get only PENDING tasks (not completed/cancelled)

    pending_tasks = await tasks_collection.find(

        {"userId": user_id, "status": "pending"},

        {"description": 1, "due_date": 1, "status": 1}  # Only essential fields

    ).limit(20).to_list(20)

    

    # Format response

    return {

        "user": {

            "id": str(user_id),

            "email": user.email,

            "name": user.name

        },

        "activeSession": {

            "sessionId": active_session.get("sessionId") if active_session else None,

            "messageCount": len(active_session.get("messages", [])) if active_session else 0,

            "recentMessages": active_session.get("messages", [])[-10:] if active_session else []

        },

        "pendingTasks": [

            {

                "id": str(t["_id"]),

                "description": t.get("description"),

                "dueDate": t.get("due_date"),

                "status": t.get("status")

            }

            for t in pending_tasks

        ],

        "reconnectedAt": datetime.now(timezone.utc).isoformat()

    }



# Simple Chat endpoint for testing

@app.post("/api/chat/send")

async def send_message(message_data: dict, user: dict = Depends(get_current_user_from_session)):

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

app.include_router(tasks.router, tags=["Tasks"])

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



        # Neo4j - Verify connectivity

        from app.db.neo4j_client import neo4j_client

        from app.config import settings as config_settings

        neo4j_uri = config_settings.NEO4J_URI

        neo4j_db_name = neo4j_uri.split('//')[-1].split('.')[0] if '//' in neo4j_uri else 'neo4j'

        

        if neo4j_client.is_available:

            connection_ok = await neo4j_client.verify_connectivity()

            if connection_ok:

                print(f"✅ Neo4j connected index : {neo4j_db_name}")

            else:

                print(f"⚠️ Neo4j driver created but connection failed")

                print(f"💡 Run: python test_neo4j_connection.py for diagnostics")

        else:

            print(f"⚠️ Neo4j not configured (operations will be skipped)")

            

    except Exception as e:

        print(f"❌ Database initialization error: {e}")



# 🚀 PRODUCTION: Scheduler removed from API server

# ❌ Email sending now handled by separate email_worker.py process

# Run: python email_worker.py in separate terminal



@app.on_event("startup")

async def _startup():

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
    from app.config import settings
    
    # Production mode: no reload
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=not settings.is_production,
        reload_dirs=["app"] if settings.is_development else None,
        reload_excludes=[".venv/*", "**/__pycache__/**", "*.pyc"] if settings.is_development else None,
    )


