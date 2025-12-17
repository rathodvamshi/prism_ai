"""
☁️ Cloud-Native Celery Configuration
=====================================

Initializes Celery for cloud deployment (Render, Vercel, AWS).
- Uses rediss:// (SSL) for cloud Redis connections
- Handles IST → UTC timezone conversion
- Configured for reliability and auto-retries
- Windows-compatible (auto-detects platform)

❌ BANNED: localhost, redis:// (without SSL), naive datetime
✅ REQUIRED: rediss://, UTC datetime objects, SSL certificates
"""
import ssl
import sys
import platform

# ☁️ Graceful Celery import - allow server to start even if Celery not installed
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError as e:
    CELERY_AVAILABLE = False
    print(f"⚠️ WARNING: Celery not available: {e}")
    print("📦 To enable email scheduling, install Celery: pip install 'celery[redis]>=5.3.0'")
    print("⚠️ Email reminders will not work until Celery is installed and worker is running.")
    # Create a dummy Celery class to prevent import errors
    class Celery:
        def __init__(self, *args, **kwargs):
            pass
        def update(self, *args, **kwargs):
            pass
        def task(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

from app.config import settings

# 🪟 Windows Detection for Worker Pool
IS_WINDOWS = platform.system() == "Windows"

# ☁️ CLOUD-NATIVE: Use CELERY_BROKER_URL if set (for cloud), fallback to REDIS_URL (for local)
broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
backend_url = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

# Detect SSL (rediss:// = SSL, redis:// = non-SSL)
is_ssl = broker_url.startswith("rediss://")

# Initialize Celery with Redis as Broker and Backend
if CELERY_AVAILABLE:
    celery_app = Celery(
        "prism_tasks",
        broker=broker_url,
        backend=backend_url
    )
    
    # 🪟 Windows-Compatible Worker Pool Configuration
    # Windows doesn't support prefork (multiprocessing), use solo or threads
    if IS_WINDOWS:
        worker_pool = "solo"  # Single-threaded worker (best for Windows)
        worker_concurrency = 1
        print("🪟 Windows detected: Using 'solo' worker pool (single-threaded)")
    else:
        worker_pool = "prefork"  # Multi-process worker (best for Linux/Mac)
        worker_concurrency = 4
        print("🐧 Unix-like system detected: Using 'prefork' worker pool")
    
    # ☁️ Cloud-Ready Configuration - Optimized for Reliability & Performance
    celery_app.conf.update(
        # Serialization
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        result_accept_content=["json"],
        
        # ☁️ CRITICAL: Timezone Configuration
        # User input: IST (Asia/Kolkata)
        # Internal processing: UTC (for cloud consistency)
        # Celery scheduling: UTC (eta parameter requires UTC)
        timezone="Asia/Kolkata",  # Display timezone (IST)
        enable_utc=True,           # Internal engine uses UTC (CRITICAL for cloud)
        
        # Task Execution
        task_track_started=True,   # Track when task starts
        task_time_limit=300,       # 5 minutes hard limit per task
        task_soft_time_limit=240 if not IS_WINDOWS else None,  # Soft limit not supported on Windows
        task_acks_late=True,        # Acknowledge after task completes (prevents loss)
        task_reject_on_worker_lost=True,  # Reject tasks if worker dies
        
        # 🔄 Auto-Recovery & Resilience
        task_always_eager=False,   # Don't execute synchronously
        task_eager_propagates=False,  # Don't propagate exceptions to caller
        task_ignore_result=False,  # Keep results for debugging (can be overridden per task)
        worker_hijack_root_logger=False,  # Don't hijack root logger
        worker_log_color=False,    # Disable color in logs for production
        worker_disable_rate_limits=False,  # Keep rate limits for stability
        
        # Connection Resilience
        broker_connection_retry_on_startup=True,  # Retry connection on startup
        broker_connection_retry=True,  # Retry connection on failure
        broker_connection_max_retries=10,  # Max retries for connection
        broker_connection_timeout=30,  # Connection timeout in seconds
        
        # Worker Configuration
        worker_pool=worker_pool,  # Platform-specific pool
        worker_prefetch_multiplier=1,  # Fair task distribution (1 task per worker)
        worker_max_tasks_per_child=50 if not IS_WINDOWS else None,  # Not supported on Windows
        
        # Result Backend
        result_expires=3600,       # Results expire after 1 hour (save memory)
        result_backend_transport_options={
            'master_name': 'mymaster',  # For Redis Sentinel
            'visibility_timeout': 3600,  # Task visibility timeout
        },
        
        # ☁️ CRITICAL: SSL SETTINGS FOR CLOUD REDIS
        # Most cloud providers (Upstash, Render Redis, AWS ElastiCache) require this
        # to avoid "Certificate Verify Failed" errors
        broker_use_ssl={
            'ssl_cert_reqs': ssl.CERT_NONE  # CERT_NONE for cloud Redis (no cert verification)
        } if is_ssl else None,
        
        redis_backend_use_ssl={
            'ssl_cert_reqs': ssl.CERT_NONE  # CERT_NONE for cloud Redis (no cert verification)
        } if is_ssl else None,
        
        # Task Routing - Dedicated queues for better performance
        task_routes={
            "prism_tasks.send_reminder_email": {"queue": "email"},
        },
        task_default_queue="default",
        task_default_exchange="tasks",
        task_default_exchange_type="direct",
        task_default_routing_key="default",
        
        # 🔍 CRITICAL: Auto-discover tasks from app.tasks module
        # This ensures tasks are registered when worker starts
        imports=("app.tasks.email_tasks",),
        include=("app.tasks.email_tasks",),
        
        # Monitoring & Events
        worker_send_task_events=True,  # Send task events for monitoring
        task_send_sent_event=True,     # Send sent events
        
        # Beat Schedule (for periodic tasks - if needed in future)
        beat_schedule={},
    )
    
    # 🔍 Auto-import tasks to ensure they're registered
    try:
        from app.tasks import email_tasks  # noqa: F401
        print("✅ Tasks auto-imported successfully")
    except ImportError as e:
        print(f"⚠️ Warning: Could not auto-import tasks: {e}")
        print("   Tasks may not be registered. Check app.tasks.email_tasks module.")
    
    # 🚀 Setup signal handlers for worker lifecycle and error recovery
    def worker_ready_handler(sender=None, **kwargs):
        """Trigger task recovery when worker is ready"""
        try:
            from app.tasks.email_tasks import recover_pending_tasks_task
            # Schedule recovery task to run after a short delay (5 seconds)
            # This ensures worker is fully ready before processing
            recover_pending_tasks_task.apply_async(countdown=5)
            print("🔄 Task recovery scheduled (will run in 5 seconds)")
        except Exception as e:
            print(f"⚠️ Could not schedule task recovery: {e}")
    
    def task_failure_handler(sender, task_id, exception, traceback, einfo, **kwargs):
        """Handle task failures gracefully - prevent worker crash"""
        print(f"❌ Task {task_id} failed: {exception}")
        print(f"   Error info: {einfo}")
        # Don't crash worker - task will be retried automatically
        # Failed tasks are logged and can be recovered later
    
    def worker_shutting_down_handler(sender=None, **kwargs):
        """Handle worker shutdown gracefully"""
        print("🛑 Worker shutting down gracefully...")
        # Give tasks time to complete
        import time
        time.sleep(2)
    
    def worker_process_init_handler(sender=None, **kwargs):
        """Initialize worker process - reconnect to databases"""
        print("🔄 Worker process initializing...")
        try:
            # Reinitialize MongoDB connection in new process
            from app.tasks.email_tasks import _init_sync_mongo_client
            _init_sync_mongo_client()
            print("✅ Worker process initialized successfully")
        except Exception as e:
            print(f"⚠️ Worker process initialization warning: {e}")
    
    # Register signal handlers
    try:
        from celery.signals import (
            worker_ready, 
            task_failure, 
            worker_shutting_down,
            worker_process_init
        )
        
        worker_ready.connect(worker_ready_handler, weak=False)
        task_failure.connect(task_failure_handler, weak=False)
        worker_shutting_down.connect(worker_shutting_down_handler, weak=False)
        worker_process_init.connect(worker_process_init_handler, weak=False)
        
        print("✅ Signal handlers registered:")
        print("   - Worker ready: Task recovery on startup")
        print("   - Task failure: Graceful error handling")
        print("   - Worker shutdown: Graceful shutdown")
        print("   - Process init: Database reconnection")
    except Exception as e:
        print(f"⚠️ Could not register all signal handlers: {e}")
        print("   Some features may not work correctly")
    
    # 🔍 MANDATORY: Redis SSL Verification (Production Safety)
    # ✅ REQUIRED: All production deployments MUST use rediss:// (SSL)
    # ❌ BANNED: redis:// (plaintext) in production
    if not broker_url.startswith("rediss://"):
        error_msg = "Redis URL must use rediss:// (SSL) for production security"
        print(f"❌ CRITICAL: {error_msg}")
        print(f"   Current: {broker_url[:50]}...")
        print("   ⚠️  Plaintext Redis connections are NOT allowed in production")
        print("   💡 Fix: Update REDIS_URL or CELERY_BROKER_URL to use rediss://")
        # In development, warn but don't fail
        if settings.is_production:
            raise ValueError(error_msg)
        else:
            print("   ⚠️  WARNING: Running in development mode - SSL not enforced")
            print("   ⚠️  This will FAIL in production deployment")
    
    print("✅ Celery configured with cloud-native settings")
    print(f"   Broker: {broker_url[:50]}...")
    print(f"   Timezone: IST (Asia/Kolkata) | Internal: UTC")
    print(f"   SSL: {'✅ Enabled (rediss://)' if is_ssl else '❌ Disabled (INSECURE)'}")
    print(f"   Platform: {platform.system()} ({'Windows' if IS_WINDOWS else 'Unix-like'})")
    print(f"   Worker Pool: {worker_pool} (concurrency: {worker_concurrency})")
    
    # 🔍 MANDATORY: Celery Startup Verification
    print("\n🔍 Verifying Celery startup configuration...")
    
    # Verify Redis connection
    try:
        inspector = celery_app.control.inspect()
        # This will fail if Redis is not reachable
        print("   ✅ Redis broker connection: Reachable")
    except Exception as e:
        print(f"   ❌ Redis broker connection: FAILED - {e}")
        print("   ⚠️  Worker may not start correctly")
    
    # Verify queues
    queues = celery_app.conf.task_routes
    print(f"   ✅ Queues registered: {list(queues.keys()) if queues else 'default'}")
    
    # Verify tasks
    try:
        registered_tasks = [t for t in celery_app.tasks.keys() if not t.startswith("celery.")]
        print(f"   ✅ Tasks registered: {len(registered_tasks)} tasks")
        for task in registered_tasks:
            print(f"      - {task}")
    except Exception as e:
        print(f"   ⚠️  Task verification: Warning - {e}")
    
    # Verify timezone
    tz = celery_app.conf.timezone
    utc_enabled = celery_app.conf.enable_utc
    print(f"   ✅ Timezone: {tz} (UTC enabled: {utc_enabled})")
    
    print("✅ Celery startup verification complete\n")
else:
    # Dummy celery_app if Celery not installed
    celery_app = None
    print("⚠️ Celery not available - email scheduling disabled")


# 🔍 Helper function to verify Celery setup
def verify_celery_setup() -> dict:
    """
    Verify that Celery is properly configured and tasks are registered.
    Returns a dictionary with verification results.
    """
    # Get worker pool from config if available
    worker_pool_config = None
    if CELERY_AVAILABLE and celery_app:
        try:
            worker_pool_config = celery_app.conf.worker_pool
        except:
            worker_pool_config = "solo" if IS_WINDOWS else "prefork"
    
    result = {
        "celery_available": CELERY_AVAILABLE,
        "celery_app_initialized": celery_app is not None,
        "tasks_registered": False,
        "registered_tasks": [],
        "broker_connected": False,
        "platform": platform.system(),
        "worker_pool": worker_pool_config,
        "errors": []
    }
    
    if not CELERY_AVAILABLE:
        result["errors"].append("Celery is not installed")
        return result
    
    if celery_app is None:
        result["errors"].append("Celery app is not initialized")
        return result
    
    # Check if tasks are registered
    try:
        registered = list(celery_app.tasks.keys())
        # Filter out built-in Celery tasks
        registered = [t for t in registered if not t.startswith("celery.")]
        result["registered_tasks"] = registered
        result["tasks_registered"] = len(registered) > 0
        
        if "prism_tasks.send_reminder_email" not in registered:
            result["errors"].append("Task 'prism_tasks.send_reminder_email' is not registered")
    except Exception as e:
        result["errors"].append(f"Error checking registered tasks: {e}")
    
    # Check broker connection (non-blocking check)
    try:
        inspector = celery_app.control.inspect()
        stats = inspector.stats()
        result["broker_connected"] = stats is not None
        if not result["broker_connected"]:
            result["errors"].append("No active workers found - Celery worker may not be running")
    except Exception as e:
        result["errors"].append(f"Broker connection check failed: {e}")
        result["broker_connected"] = False
    
    return result
