"""
Celery Tasks for Email Reminders
=================================

Handles scheduled email sending with automatic retries and IST timezone support.
- Automatic recovery of pending/overdue tasks on worker startup
- Production-ready error handling and retry logic
- Timezone-aware scheduling (IST → UTC conversion)
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import asyncio
from typing import Dict, Any, List
import logging

from app.services.email_service import send_professional_email
from app.config import settings
from bson import ObjectId

# Setup logging
logger = logging.getLogger(__name__)

# ☁️ Graceful Celery import
try:
    from app.core.celery_app import celery_app, CELERY_AVAILABLE
    if not CELERY_AVAILABLE or celery_app is None:
        raise ImportError("Celery not available")
except ImportError:
    print("⚠️ WARNING: Celery not available - email tasks will not work")
    celery_app = None
    CELERY_AVAILABLE = False

# IST timezone for display
IST = ZoneInfo("Asia/Kolkata")

# Synchronous MongoDB client for Celery tasks
_sync_mongo_client = None
_sync_tasks_collection = None

# ⚠️ CRITICAL SAFETY NOTE: PyMongo Collection Objects
# ====================================================
# NEVER use truthiness checks on PyMongo Collection objects!
# ❌ WRONG: if collection: ...
# ❌ WRONG: collection or fallback
# ❌ WRONG: if not collection: ...
# ✅ CORRECT: if collection is not None: ...
# ✅ CORRECT: Use _get_tasks_collection_safe() helper function
# ====================================================

def _mask_uri(uri: str) -> str:
    """Mask sensitive information in URI for logging"""
    try:
        if '@' in uri:
            parts = uri.split('@', 1)
            userinfo = parts[0]
            host = parts[1] if len(parts) > 1 else ''
            if ':' in userinfo:
                user, _ = userinfo.split(':', 1)
                masked = f"{user}:***@{host[:30]}..."
            else:
                masked = f"{userinfo[:10]}:***@{host[:30]}..."
            return masked
        return uri[:50] + "..."
    except:
        return uri[:50] + "..."

def _get_tasks_collection_safe():
    """
    ✅ SAFE MongoDB Collection Getter
    
    NEVER use truthiness checks on PyMongo Collection objects.
    This function provides a safe way to get the collection.
    
    Returns:
        Collection object or None (never raises truthiness errors)
    """
    if _sync_tasks_collection is not None:
        return _sync_tasks_collection
    return _init_sync_mongo_client()

def _init_sync_mongo_client():
    """
    Initialize synchronous MongoDB client for Celery tasks (lazy initialization).
    Handles special characters in username/password with proper URL encoding.
    """
    global _sync_mongo_client, _sync_tasks_collection
    
    if _sync_tasks_collection is not None:
        return _sync_tasks_collection
    
    try:
        from pymongo import MongoClient
        from urllib.parse import urlparse, quote_plus, unquote_plus, urlsplit, urlunsplit
        import re
        
        logger.info("🔄 Initializing synchronous MongoDB client for Celery...")
        
        # ☁️ CRITICAL: Enhanced MongoDB URI sanitization
        # Handle special characters in username/password (especially @, :, /, etc.)
        original_uri = settings.MONGO_URI
        
        def sanitize_mongo_uri_enhanced(uri: str) -> str:
            """Enhanced sanitization with better error handling"""
            try:
                # Check if URI is already properly formatted
                if not uri or not uri.startswith(('mongodb://', 'mongodb+srv://')):
                    raise ValueError(f"Invalid MongoDB URI format: {uri[:50]}...")
                
                # Use the existing sanitization function first
                from app.db.mongo_client import _sanitize_mongo_uri
                sanitized = _sanitize_mongo_uri(uri)
                
                # Additional validation: try to parse it
                try:
                    parsed = urlsplit(sanitized)
                    # If parsing succeeds, return sanitized URI
                    return sanitized
                except Exception as parse_error:
                    logger.warning(f"URI parsing failed after sanitization: {parse_error}")
                    # Fallback: manual encoding
                    return _manual_encode_mongo_uri(uri)
                    
            except Exception as e:
                logger.warning(f"Sanitization failed, using manual encoding: {e}")
                return _manual_encode_mongo_uri(uri)
        
        def _manual_encode_mongo_uri(uri: str) -> str:
            """Manual URI encoding as fallback"""
            try:
                # Extract scheme
                if uri.startswith('mongodb+srv://'):
                    scheme = 'mongodb+srv://'
                    rest = uri[14:]  # Remove 'mongodb+srv://'
                elif uri.startswith('mongodb://'):
                    scheme = 'mongodb://'
                    rest = uri[10:]  # Remove 'mongodb://'
                else:
                    raise ValueError(f"Unknown MongoDB URI scheme: {uri[:50]}")
                
                # Split at @ to separate credentials from host
                if '@' not in rest:
                    # No credentials, return as-is
                    return uri
                
                # Find the LAST @ (host separator)
                parts = rest.rsplit('@', 1)
                if len(parts) != 2:
                    raise ValueError(f"Invalid URI format: multiple @ symbols or missing host")
                
                userinfo, host_and_path = parts
                
                # Split userinfo into username:password
                if ':' in userinfo:
                    user, pwd = userinfo.split(':', 1)
                    # URL encode username and password
                    safe_user = quote_plus(unquote_plus(user))
                    safe_pwd = quote_plus(unquote_plus(pwd))
                    encoded_userinfo = f"{safe_user}:{safe_pwd}"
                else:
                    # Only username, no password
                    safe_user = quote_plus(unquote_plus(userinfo))
                    encoded_userinfo = safe_user
                
                # Reconstruct URI
                return f"{scheme}{encoded_userinfo}@{host_and_path}"
                
            except Exception as e:
                logger.error(f"Manual encoding failed: {e}")
                raise
        
        # Sanitize the URI
        logger.debug(f"Original URI (masked): {_mask_uri(original_uri)}")
        sanitized_uri = sanitize_mongo_uri_enhanced(original_uri)
        logger.debug(f"Sanitized URI (masked): {_mask_uri(sanitized_uri)}")
        
        # Validate sanitized URI format
        if not sanitized_uri.startswith(('mongodb://', 'mongodb+srv://')):
            raise ValueError(f"Invalid MongoDB URI format after sanitization")
        
        # Parse MongoDB URI to extract database name
        parsed_uri = urlparse(sanitized_uri)
        db_path = parsed_uri.path.strip("/")
        
        # Extract database name from URI path, default to "prism_db" (matches async client)
        if db_path:
            # Path might be "/database_name" or "database_name"
            db_name = db_path.split("/")[0] if "/" in db_path else db_path
        else:
            # No database in URI, use default (matches mongo_client.py)
            db_name = "prism_db"
        
        logger.info(f"📊 Database name extracted: {db_name}")
        
        # For mongodb+srv, we need to keep the full URI
        # For mongodb://, we can remove the path if needed
        if sanitized_uri.startswith('mongodb+srv://'):
            # mongodb+srv doesn't support database in path, use full URI
            clean_uri = sanitized_uri
        else:
            # Remove database from URI path if present
            if parsed_uri.path:
                clean_uri = sanitized_uri.replace(parsed_uri.path, "")
            else:
                clean_uri = sanitized_uri
        
        logger.debug(f"Connecting to MongoDB...")
        
        # Initialize synchronous MongoDB client
        _sync_mongo_client = MongoClient(
            clean_uri,
            serverSelectionTimeoutMS=10000,  # 10 second timeout
            connectTimeoutMS=10000,
            socketTimeoutMS=30000,
            retryWrites=True,
            retryReads=True,
        )
        
        logger.debug(f"MongoClient created, testing connection...")
        
        # Get database (use extracted name or default)
        _sync_db = _sync_mongo_client.get_database(db_name)
        _sync_tasks_collection = _sync_db.tasks
        
        # Test connection with timeout
        logger.debug(f"Pinging MongoDB server...")
        _sync_mongo_client.admin.command('ping', maxTimeMS=5000)
        
        logger.info(f"✅ Synchronous MongoDB client initialized successfully")
        logger.info(f"   Database: {db_name}")
        logger.info(f"   Collection: tasks")
        logger.info(f"   Connection: Active")
        
        return _sync_tasks_collection
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to initialize sync MongoDB client")
        logger.error(f"   Error: {error_msg}")
        logger.error(f"   URI (masked): {_mask_uri(settings.MONGO_URI)}")
        
        # Provide helpful error message
        if "Reserved characters" in error_msg or "RFC" in error_msg:
            logger.error(f"   💡 Hint: Password contains special characters that need URL encoding")
            logger.error(f"   💡 Solution: Ensure password is properly encoded in MONGO_URI")
            logger.error(f"   💡 Special chars (@, :, /, etc.) should be encoded (e.g., @ → %40)")
        
        import traceback
        logger.debug(f"Full traceback:\n{traceback.format_exc()}")
        
        _sync_tasks_collection = None
        _sync_mongo_client = None
        return None

# Initialize on module load (deferred - will initialize when needed)
# This allows Celery to start even if MongoDB connection fails initially
try:
    # Try to initialize, but don't fail if it doesn't work
    _init_sync_mongo_client()
except Exception as e:
    logger.warning(f"⚠️ MongoDB initialization deferred: {e}")
    logger.info("   Connection will be retried when tasks are executed")


def _sync_email_send(task_data: Dict[str, Any]) -> bool:
    """
    Synchronous wrapper for async email sending.
    Celery tasks must be synchronous, so we use asyncio.run().
    """
    try:
        return asyncio.run(send_professional_email(task_data, retry_count=0, max_retries=3))
    except Exception as e:
        print(f"❌ Sync email wrapper error: {e}")
        raise


# ☁️ Only register task if Celery is available
if CELERY_AVAILABLE and celery_app:
    
    @celery_app.task(
        bind=True,
        name="prism_tasks.send_reminder_email",
        autoretry_for=(Exception,),  # Retry on ANY error
        retry_backoff=True,          # Exponential backoff: 1s, 2s, 4s, 8s, 16s...
        retry_backoff_max=300,       # Max 5 minutes between retries
        retry_jitter=True,           # Add randomness to prevent thundering herd
        retry_kwargs={'max_retries': 3},  # Max 3 retries (4 total attempts)
        queue="email",               # Dedicated email queue
        ignore_result=True,          # Don't store results (save Redis memory)
        time_limit=300,              # 5 minute hard timeout
        reject_on_worker_lost=True,  # Reject if worker dies (prevents loss)
        acks_late=True,              # Acknowledge after completion
    )
    def send_reminder_email_task(self, task_id: str):
        """
        Celery task to send reminder email at scheduled time.
        
        Args:
            task_id: MongoDB ObjectId string of the task
        
        This task is scheduled with `apply_async(eta=...)` from the /confirm endpoint.
        Celery will wait until the `eta` time before executing this task.
        """
        current_time_ist = datetime.now(IST)
        logger.info(f"👷 Processing Task {task_id} at {current_time_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")
        
        try:
            # Lazy initialization of MongoDB client (retry if failed on startup)
            # Retry connection up to 3 times with exponential backoff
            # ✅ CRITICAL: Use safe getter - PyMongo collections cannot be truthy
            tasks_collection = None
            max_connection_retries = 3
            for attempt in range(max_connection_retries):
                tasks_collection = _get_tasks_collection_safe()
                
                if tasks_collection is not None:
                    break
                    
                if attempt < max_connection_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(f"⚠️ MongoDB connection failed, retrying in {wait_time}s (attempt {attempt + 1}/{max_connection_retries})")
                    import time
                    time.sleep(wait_time)
            
            if tasks_collection is None:
                error_msg = "Sync MongoDB client not available - connection failed after retries"
                logger.error(f"❌ {error_msg}")
                # Don't crash worker - raise exception for Celery retry mechanism
                raise ConnectionError(error_msg)
            
            # 1. Fetch Task from MongoDB (synchronous)
            obj_id = ObjectId(task_id)
            task = tasks_collection.find_one({"_id": obj_id})
            
            if not task:
                error_msg = f"Task {task_id} not found in database"
                logger.warning(f"⚠️ {error_msg} - Skipping")
                return {"status": "skipped", "reason": "task_not_found", "error": error_msg}
            
            # 2. Check if already completed (Safety Check - prevents duplicate emails)
            if task.get("status") == "completed":
                error_msg = f"Task {task_id} already completed - preventing duplicate email"
                logger.info(f"ℹ️ {error_msg}")
                return {"status": "skipped", "reason": "already_completed", "error": error_msg}
            
            # 2.5. Check if email was already sent (additional safety check)
            if task.get("email_status") == "sent" and task.get("email_sent_at"):
                error_msg = f"Task {task_id} email already sent at {task.get('email_sent_at')}"
                logger.info(f"ℹ️ {error_msg}")
                return {"status": "skipped", "reason": "email_already_sent", "error": error_msg}
            
            # 3. Validate required fields
            user_email = task.get("user_email") or task.get("email")
            if not user_email:
                error_msg = f"Task {task_id} has no user_email field - cannot send reminder"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            # 4. Prepare task data for email service
            # Use display_time if available (shows IST to user), otherwise format due_date
            display_time = task.get("display_time") or (
                task.get("due_date").strftime("%Y-%m-%d %I:%M %p IST") 
                if isinstance(task.get("due_date"), datetime) 
                else "scheduled time"
            )
            
            task_data = {
                "user_name": task.get("user_name") or user_email.split("@")[0] if user_email else "Friend",
                "user_email": user_email,
                "description": task.get("description", "Your scheduled task"),
                "due_date": task.get("due_date"),
                "display_time": display_time,  # Human-readable IST time for email
            }
            
            logger.info(f"📧 Preparing to send email to {user_email}")
            logger.info(f"   Task: {task_data['description']}")
            logger.info(f"   Due: {display_time}")
            
            # 5. Send Email (Synchronous wrapper)
            try:
                email_sent = _sync_email_send(task_data)
                
                if not email_sent:
                    error_msg = "Email sending returned False - SendGrid may have failed silently"
                    logger.error(f"❌ {error_msg}")
                    raise Exception(error_msg)
            except Exception as email_error:
                logger.error(f"❌ Email sending failed: {email_error}")
                raise
            
            # 6. Mark Task as Completed in MongoDB (synchronous)
            now_utc = datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)
            update_result = tasks_collection.update_one(
                {"_id": obj_id},
                {
                    "$set": {
                        "status": "completed",
                        "email_status": "sent",
                        "email_sent_at": now_utc,
                        "updated_at": now_utc,
                    }
                }
            )
            
            if update_result.modified_count == 0:
                logger.warning(f"⚠️ Task {task_id} status update returned 0 modified documents (may already be updated)")
            else:
                logger.info(f"✅ Task {task_id} marked as completed in database")
            
            success_msg = f"✅ Reminder sent successfully to {user_email} for task: {task_data['description']}"
            logger.info(success_msg)
            
            return {
                "status": "success",
                "task_id": task_id,
                "email_sent_at": now_utc.isoformat(),
                "user_email": user_email,
                "description": task_data["description"]
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error processing task {task_id}: {error_msg}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Get retry count
            retry_count = 0
            max_retries = 3
            if hasattr(self, 'request'):
                retry_count = getattr(self.request, 'retries', 0)
                max_retries = getattr(self.request, 'max_retries', 3)
            
            # Update task with error status (synchronous)
            # ✅ CRITICAL: Use safe getter - PyMongo collections cannot be truthy
            try:
                error_collection = _get_tasks_collection_safe()
                    
                if error_collection is not None:
                    obj_id = ObjectId(task_id)
                    
                    # Mark as permanently failed if max retries reached
                    if retry_count >= max_retries:
                        error_collection.update_one(
                            {"_id": obj_id},
                            {
                                "$set": {
                                    "email_status": "permanently_failed",
                                    "email_last_error": f"{error_msg} (max retries reached)",
                                    "email_last_attempt": datetime.now(timezone.utc).replace(tzinfo=None),
                                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                                },
                                "$inc": {"email_retry_count": 1}
                            }
                        )
                        logger.error(f"❌ Task {task_id} permanently failed after {retry_count + 1} attempts")
                        # Don't re-raise - task is done, will be recovered by recovery task
                        return {
                            "status": "permanently_failed",
                            "task_id": task_id,
                            "error": error_msg,
                            "retries": retry_count + 1
                        }
                    else:
                        error_collection.update_one(
                            {"_id": obj_id},
                            {
                                "$set": {
                                    "email_status": "failed",
                                    "email_last_error": error_msg,
                                    "email_last_attempt": datetime.now(timezone.utc).replace(tzinfo=None),
                                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                                },
                                "$inc": {"email_retry_count": 1}
                            }
                        )
                        logger.warning(f"⚠️ Task {task_id} failed (attempt {retry_count + 1}/{max_retries + 1}), will retry")
            except Exception as update_error:
                logger.error(f"⚠️ Failed to update task error status: {update_error}")
            
            # Re-raise to trigger Celery retry (with exponential backoff) if not at max retries
            if retry_count < max_retries:
                raise
            else:
                # Max retries reached, don't crash worker
                logger.error(f"❌ Task {task_id} exceeded max retries, marking as permanently failed")
                return {
                    "status": "permanently_failed",
                    "task_id": task_id,
                    "error": error_msg,
                    "retries": retry_count + 1
                }
    
    @celery_app.task(
        bind=True,
        name="prism_tasks.health_check",
        queue="default",
        ignore_result=False,
    )
    def health_check_task(self):
        """
        🏥 HEALTH CHECK: Monitor worker health and database connections.
        Can be called periodically to ensure system is healthy.
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {}
        }
        
        # Check MongoDB connection
        # ✅ CRITICAL: Use safe getter - PyMongo collections cannot be truthy
        try:
            tasks_collection = _get_tasks_collection_safe()
                
            if tasks_collection is not None:
                # Test query
                tasks_collection.find_one({}, {"_id": 1})
                health_status["checks"]["mongodb"] = "ok"
            else:
                health_status["checks"]["mongodb"] = "failed"
                health_status["status"] = "unhealthy"
        except Exception as e:
            health_status["checks"]["mongodb"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"
        
        # Check Redis connection (via Celery broker)
        try:
            from app.core.celery_app import celery_app
            inspector = celery_app.control.inspect()
            stats = inspector.stats()
            if stats:
                health_status["checks"]["redis"] = "ok"
            else:
                health_status["checks"]["redis"] = "no_workers"
        except Exception as e:
            health_status["checks"]["redis"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"
        
        logger.info(f"🏥 Health check: {health_status['status']}")
        return health_status
    
    @celery_app.task(
        bind=True,
        name="prism_tasks.recover_pending_tasks",
        queue="default",
        ignore_result=True,
        autoretry_for=(Exception,),
        retry_backoff=True,
        retry_backoff_max=60,
        retry_kwargs={'max_retries': 2},
    )
    def recover_pending_tasks_task(self):
        """
        🚀 STARTUP TASK: Recover pending/overdue tasks when Celery worker starts.
        This ensures no tasks are missed if the worker was down.
        Automatically triggered on worker startup via signal handler.
        """
        logger.info("🔄 Starting task recovery process...")
        
        try:
            # ✅ CRITICAL: Use safe getter - PyMongo collections cannot be truthy
            tasks_collection = _get_tasks_collection_safe()
                
            if tasks_collection is None:
                logger.error("❌ Cannot recover tasks: MongoDB client not available")
                return {"status": "error", "reason": "mongodb_unavailable"}
            
            now_utc = datetime.now(timezone.utc)
            
            # Find all pending tasks that are due (or overdue)
            # Status: pending, due_date <= now, email_status != sent
            # Also recover permanently_failed tasks (they may have been fixed)
            pending_tasks = list(tasks_collection.find({
                "status": "pending",
                "due_date": {"$lte": now_utc},
                "$or": [
                    {"email_status": {"$exists": False}},
                    {"email_status": {"$ne": "sent"}},
                    {"email_status": "failed"},  # Retry failed tasks
                    {"email_status": "permanently_failed"}  # Retry permanently failed (may have been fixed)
                ]
            }).limit(100))  # Process max 100 at a time to avoid overload
            
            recovered_count = 0
            scheduled_count = 0
            
            for task in pending_tasks:
                try:
                    task_id = str(task["_id"])
                    due_date = task.get("due_date")
                    
                    # If task is overdue, send immediately (eta=now)
                    # If task is due soon, schedule with original eta
                    if isinstance(due_date, datetime):
                        if due_date.tzinfo is None:
                            due_date = due_date.replace(tzinfo=timezone.utc)
                        elif due_date.tzinfo != timezone.utc:
                            due_date = due_date.astimezone(timezone.utc)
                        
                        # Schedule task (immediately if overdue, or at due time if future)
                        eta_time = max(now_utc, due_date)
                        
                        # Use task name string to avoid circular reference
                        celery_app.send_task(
                            "prism_tasks.send_reminder_email",
                            args=[task_id],
                            eta=eta_time,
                            queue="email"
                        )
                        scheduled_count += 1
                        logger.info(f"✅ Recovered task {task_id} - scheduled for {eta_time}")
                    else:
                        # Invalid due_date, send immediately
                        celery_app.send_task(
                            "prism_tasks.send_reminder_email",
                            args=[task_id],
                            queue="email"
                        )
                        scheduled_count += 1
                        logger.info(f"✅ Recovered task {task_id} - sending immediately (invalid due_date)")
                    
                    recovered_count += 1
                    
                except Exception as task_error:
                    logger.error(f"❌ Error recovering task {task.get('_id')}: {task_error}")
                    continue
            
            result = {
                "status": "success",
                "recovered": recovered_count,
                "scheduled": scheduled_count
            }
            
            if recovered_count > 0:
                logger.info(f"✅ Task recovery complete: {recovered_count} tasks recovered, {scheduled_count} scheduled")
                logger.info(f"   Recovery successful - all pending tasks have been scheduled")
            else:
                logger.info("ℹ️ No pending tasks to recover - system is up to date")
            
            # Log recovery summary for monitoring
            logger.info(f"📊 Recovery Summary: {recovered_count} found, {scheduled_count} scheduled, {recovered_count - scheduled_count} skipped")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Task recovery failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"status": "error", "error": str(e)}
    
else:
    # Dummy function if Celery not available
    def send_reminder_email_task(task_id: str):
        """Dummy function when Celery is not available"""
        print(f"⚠️ Celery not available - cannot send email for task {task_id}")
        print("📦 Please install Celery: pip install 'celery[redis]>=5.3.0'")
        print("🚀 Then start Celery worker: celery -A app.core.celery_app worker --loglevel=info")
        return {"status": "error", "reason": "celery_not_available"}
    
    def recover_pending_tasks_task():
        """Dummy function when Celery is not available"""
        return {"status": "error", "reason": "celery_not_available"}
