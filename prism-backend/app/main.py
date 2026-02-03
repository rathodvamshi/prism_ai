import warnings
import logging
import sys
import threading

# =============================================================================
# 🔇 SUPPRESS NOISY LIBRARY LOGS IMMEDIATELY (before any other imports)
# =============================================================================
# PyMongo background threads cause WinError 10060 / NetworkTimeout on Windows
# These are NON-FATAL but spam the logs. Silence them at CRITICAL level.
# This must be done BEFORE any pymongo/motor imports to take effect.
# =============================================================================
for _noisy_logger in [
    'pymongo', 'pymongo.pool', 'pymongo.topology', 'pymongo.connection',
    'pymongo.serverSelection', 'pymongo.command', 'pymongo.monitor', 'motor',
    'httpcore', 'httpx', 'urllib3', 'asyncio', 'watchfiles', 'websockets',
    'neo4j', 'neo4j.io', 'neo4j.pool', 'neo4j.bolt',
]:
    logging.getLogger(_noisy_logger).setLevel(logging.CRITICAL)

# =============================================================================
# 🔇 SUPPRESS PYMONGO BACKGROUND THREAD TRACEBACKS
# =============================================================================
# PyMongo's _process_periodic_tasks runs in background threads and occasionally
# times out on Windows. These tracebacks bypass logging and print to stderr.
# We intercept threading excepthook to suppress these non-fatal errors.
# =============================================================================
_original_excepthook = threading.excepthook

def _suppress_pymongo_background_errors(args):
    """Suppress non-fatal PyMongo background thread errors."""
    exc_type = args.exc_type
    exc_value = args.exc_value
    
    # Check if this is a PyMongo NetworkTimeout from background tasks
    if exc_type and exc_type.__module__ and 'pymongo' in exc_type.__module__:
        # Silently ignore - these are background connection pool maintenance
        return
    
    # Check if it's a socket timeout in a PyMongo context
    if exc_type in (TimeoutError, ConnectionError, OSError):
        exc_str = str(exc_value) if exc_value else ''
        if any(x in exc_str for x in ['timed out', 'mongodb.net', 'yry129x']):
            return  # Silently ignore Atlas connection pool timeouts
    
    # For all other exceptions, use the original handler
    _original_excepthook(args)

threading.excepthook = _suppress_pymongo_background_errors

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
from app.routers import media
from app.routers import user, auth, chat, tasks, streaming, memory_chat, api_keys, admin, forms
from app.utils.preprocess import preprocess as safe_preprocess
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
    - Validate Configuration
    - Connect to MongoDB & Initialize Indexes
    - Start background workers
    - Initialize Caches & Pools
    
    Shutdown:
    - Stop workers gracefully
    - Close all connections
    """
    global worker_task
    
    # 0. 🛠️ Configuration Validation
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
    
    # Startup
    print("🚀 Connecting to MongoDB...")
    mongo_connected = False
    try:
        from app.db.mongo_client import db
        await connect_to_mongo()
        mongo_connected = True
        
        # 1.1 📊 Initialize Indexes
        print("📊 Initializing MongoDB Indexes...")
        try:
            # Users: unique email
            await db.users.create_index("email", unique=True)
            # User memory: unique (user_id, type, content)
            await db.user_memory.create_index([("user_id", 1), ("type", 1), ("content", 1)], unique=True)
            # Chat sessions: unique per user and sessionId
            await db.chat_sessions.create_index([("sessionId", 1), ("user_id", 1)], unique=True)
            # Highlights: uniqueKey is precomputed
            await db.message_highlights.create_index("uniqueKey", unique=True)
            # Tasks: unique taskId
            await db.user_tasks.create_index("taskId", unique=True)
            # Mini-agent threads: unique per user and thread
            await db.mini_agent_threads.create_index([("threadId", 1), ("user_id", 1)], unique=True)
            # Shared conversations: unique shareId
            await db.shared_conversations.create_index("shareId", unique=True)
            
            # API Keys & Usage (PERFORMANCE CRITICAL)
            await db.api_keys.create_index("user_id")
            await db.api_keys.create_index([("user_id", 1), ("is_active", 1)])
            await db.usage_tracking.create_index("user_id", unique=True)
            
            logger.info("✅ MongoDB Indexes verified")
        except Exception as e:
            logger.warning(f"⚠️ Index initialization failed (non-fatal): {e}")
            
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        logger.warning("⚠️ App starting in LIMITED MODE - MongoDB operations will fail")
        logger.warning("   Check your network connection and MongoDB Atlas status")
    
    # 🔐 Initialize User Resolution Service (CRITICAL for ONE EMAIL = ONE USER)
    if mongo_connected:
        print("🔐 Initializing User Resolution Service...")
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            from app.config import settings as app_settings
            from app.services.user_resolution_service import initialize_user_resolution_service
            from app.db.mongo_client import _sanitize_mongo_uri, db_instance
            
            # Reuse the global connection pool (Singleton)
            if not db_instance.client:
                 raise RuntimeError("MongoDB client not initialized before User Resolution Service")

            user_resolution_service = initialize_user_resolution_service(db_instance.client)
            
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
    else:
        logger.warning("⚠️ Skipping User Resolution Service (MongoDB not connected)")
    
    # 🚀 Initializing PERFECT Database Architecture & Services
    print("🚀 Initializing Extended Services...")
    try:
        # Redis & Semantic Cache
        from app.db.redis_client import redis_client
        await redis_client.ping()
        
        from app.services.semantic_cache import SemanticCache, COMMON_RESPONSES
        semantic_cache = SemanticCache(redis_client, ttl_hours=24)
        await semantic_cache.warm_common_queries("llama-3.1-8b-instant", COMMON_RESPONSES)
        logger.info("✅ Semantic cache initialized & warmed")

        # Connection Pool
        from app.services.request_optimizer import initialize_connection_pool
        initialize_connection_pool(settings.GROQ_API_KEY)
        
        # Pinecone
        from app.services.vector_memory_service import INDEX_NAME
        # We just log it here, service inits on its own
        
    except Exception as e:
        logger.warning(f"⚠️ Extended service initialization warning: {e}")

    # 🚀 Backend warmup on reconnect
    print("🔥 Warming up connections...")
    
    # 1. Warm Redis connection (Already done above, but safe to repeat ping)
    try:
        from app.db.redis_client import redis_client
        await redis_client.ping()
        logger.info("✅ Redis warmed up")
    except Exception as e:
        logger.warning(f"⚠️ Redis warmup failed: {e}")
    
    # 2. Warm MongoDB connection
    try:
        # db imported at top of function
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
    
    # 4. 🚀 PRE-INITIALIZE GROQ POOL (Eliminates first-request delay)
    try:
        from app.services.groq_pool import get_groq_pool
        pool = await get_groq_pool()
        logger.info(f"✅ Groq Pool pre-initialized ({len(pool.keys)} keys ready)")
    except Exception as e:
        logger.warning(f"⚠️ Groq Pool warmup failed: {e}")
    
    # 5. Schedule ONLY nearest task (not all tasks)
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



# 🚀 Part 19: Structured Logging Middleware (ULTRA-OPTIMIZED)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time

# 🚀 SKIP LOGGING FOR HIGH-FREQUENCY ENDPOINTS (Reduces overhead)
SKIP_LOGGING_PATHS = {"/health", "/api/streaming/stream/", "/static/", "/favicon.ico"}

# 🚨 SLOW REQUEST THRESHOLD (milliseconds)
SLOW_REQUEST_THRESHOLD_MS = 2000

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log every request with user_id, intent, latency
    OPTIMIZED: Skip logging for streaming/health endpoints
    ALERTS: Warns on slow requests (>2s)
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # 🚀 FAST PATH: Skip logging for high-frequency/streaming endpoints
        if any(skip in path for skip in SKIP_LOGGING_PATHS):
            return await call_next(request)
        
        start_time = time.time()
        
        # Extract user info if authenticated (lightweight)
        user_id = "anonymous"
        auth_header = request.headers.get("authorization", "")
        cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "session_id")
        session_cookie = request.cookies.get(cookie_name, "")
        
        if auth_header or session_cookie:
            user_id = "authenticated"
        
        # Extract intent from path
        intent = path.split("/")[-1] if path else "unknown"
        
        try:
            response = await call_next(request)
            latency_ms = (time.time() - start_time) * 1000
            
            # 🚨 SLOW REQUEST ALERT (>2s)
            if latency_ms > SLOW_REQUEST_THRESHOLD_MS:
                logger.warning(
                    f"🐢 SLOW REQUEST | path={path} method={request.method} "
                    f"latency_ms={latency_ms:.0f} status={response.status_code} "
                    f"⚠️ Consider optimization!"
                )
            # 🚀 Only log slow requests (>100ms) or errors to reduce noise
            elif latency_ms > 100 or response.status_code >= 400:
                logger.info(
                    f"📊 REQUEST | path={path} method={request.method} "
                    f"user={user_id} latency_ms={latency_ms:.0f} status={response.status_code}"
                )
            
            return response
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                f"⚠️ REQUEST_ERROR | path={path} method={request.method} "
                f"latency_ms={latency_ms:.0f} error={type(e).__name__}"
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

# Register Routers
app.include_router(streaming.router)
app.include_router(api_keys.router, tags=["API Keys"])
app.include_router(forms.router, tags=["Forms"])  # Contact form submissions

# 🚀 SCALABILITY: GZip Compression
# Compresses responses > 500 bytes (e.g. large chat history)
# from fastapi.middleware.gzip import GZipMiddleware
# app.add_middleware(GZipMiddleware, minimum_size=500)


# Static files for audio/images (allow missing dir in dev)
app.mount("/static", StaticFiles(directory="static", check_dir=False), name="static")


# Health Check
@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "active", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# 🚀 Performance Stats Endpoint
@app.get("/health/performance")
async def performance_stats():
    """
    Get real-time performance statistics.
    Includes cache hit rates, query latencies, and optimization metrics.
    """
    try:
        from app.utils.performance_optimizer import get_optimization_stats
        from app.db.connection_pool import get_pool_stats
        
        return {
            "status": "ok",
            "optimization": get_optimization_stats(),
            "connections": await get_pool_stats()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
    pre = safe_preprocess(user_message)
    working_text = pre["working_text"]
    user_id = user.user_id or "unknown"
    
    # Simple echo response with user context
    display_name = user.name or user.email or "User"
    response = f"Hello {display_name}! You said: {working_text}"
    
    return {
        "response": response,
        "user_id": user_id,
        "preprocessing": {
            "language_hint": pre.get("language_hint"),
            "entities": pre.get("entities"),
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Routers
app.include_router(health_llm.router, tags=["Health"])
app.include_router(user.router, tags=["User"])
app.include_router(auth.router, tags=["Auth"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(tasks.router, tags=["Tasks"])
app.include_router(highlights.router, tags=["Highlights"])
app.include_router(media.router, tags=["Media"])  # 🎵 NEW: Media Library
app.include_router(memory_chat.router, tags=["Memory Chat"]) # 🧠 NEW: Memory Graph & Consolidation
app.include_router(admin.router) # 👑 NEW: Admin Portal





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







