from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Literal
import time  # 🚀 Part 19

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db.mongo_client import tasks_collection
from app.utils.auth import get_current_user_from_session
from app.models.user_models import User
from app.services.scheduler_service import schedule_next_task
from app.services.email_queue_service import schedule_task_reminder, remove_scheduled_email
from app.services.cache_service import cache_service  # Part 10: Smart caching
from app.utils.structured_logging import log_task_operation  # 🚀 Part 19
from app.utils.idempotency import is_duplicate_task, mark_task_created  # 🚀 Part 20

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class ConfirmTaskRequest(BaseModel):
    description: str
    due_date: Optional[str] = None  # ISO or "YYYY-MM-DD HH:MM" string
    recurrence: Optional[dict] = None  # Optional recurrence rule


class TaskResponse(BaseModel):
    task_id: str
    description: str
    due_date: Optional[datetime] = None
    status: str
    recurrence: Optional[dict] = None
    email_status: Optional[str] = None
    email_retry_count: Optional[int] = None
    email_last_error: Optional[str] = None
    email_sent_at: Optional[datetime] = None
    confirmation_message: Optional[str] = None


class UpdateTaskRequest(BaseModel):
    task_id: str
    description: Optional[str] = None
    due_date: Optional[str] = None  # ISO or "YYYY-MM-DD HH:MM"
    recurrence: Optional[dict] = None


class CancelTaskRequest(BaseModel):
    task_id: str


@router.post("/confirm", response_model=TaskResponse)
async def confirm_task(
    payload: ConfirmTaskRequest,
    current_user: User = Depends(get_current_user_from_session),
):
    """
    Finalizes a task after the user confirms it in the UI.

    - Writes a pending task to MongoDB
    - Uses userId for fast lookups and scheduler compatibility
    - Prevents duplicate tasks with same description and similar due dates
    
    🚀 Part 19: Structured logging (user_id, intent, latency, errors)
    🚀 Part 20: Idempotency keys prevent duplicate submissions
    """
    start_time = time.time()  # 🚀 Part 19: Track latency
    user_id = current_user.user_id

    if not payload.description:
        raise HTTPException(status_code=400, detail="Task description is required")

    # ☁️ CLOUD-NATIVE: Parse user input as IST, convert to UTC for Celery
    # User says "9:00 PM" → We interpret as "9:00 PM IST" → Convert to UTC → Schedule on Celery
    import pytz
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Define timezones explicitly
    IST = pytz.timezone('Asia/Kolkata')
    UTC = pytz.utc
    
    # 🚀 GOLDEN RULE LOGGING: Track all time calculations
    now_ist = datetime.now(IST)
    logger.info(f"[TIME] 🎯 TASK CREATION DEBUG")
    logger.info(f"[TIME] Raw user input: {payload.description}")
    logger.info(f"[TIME] Received due_date: {payload.due_date}")
    logger.info(f"[TIME] Current IST time: {now_ist.strftime('%Y-%m-%d %I:%M %p IST')}")
    
    # ☁️ Parse due_date string into datetime if provided
    # Frontend may send null/undefined, so we need to handle that gracefully
    due_dt: Optional[datetime] = None
    if not payload.due_date:
        logger.error(f"❌ Task confirmation failed: due_date is missing for user {user_id}")
        raise HTTPException(
            status_code=400, 
            detail="due_date is required. Please provide a date and time for the reminder."
        )
    
    try:
        # Try flexible parsing: allow full ISO or simple "YYYY-MM-DD HH:MM"
        try:
            # Handle ISO format with 'Z' (UTC) or timezone offset
            date_str = payload.due_date.replace('Z', '+00:00')
            due_dt = datetime.fromisoformat(date_str)
            logger.info(f"✅ Parsed due_date as ISO: {payload.due_date} → {due_dt}")
        except ValueError:
            # Try common formats
            try:
                due_dt = datetime.strptime(payload.due_date, "%Y-%m-%d %H:%M")
                logger.info(f"✅ Parsed due_date as 'YYYY-MM-DD HH:MM': {payload.due_date} → {due_dt}")
            except ValueError:
                try:
                    due_dt = datetime.strptime(payload.due_date, "%Y-%m-%d %H:%M:%S")
                    logger.info(f"✅ Parsed due_date as 'YYYY-MM-DD HH:MM:SS': {payload.due_date} → {due_dt}")
                except ValueError:
                    logger.error(f"❌ Failed to parse due_date: {payload.due_date}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Invalid due_date format: '{payload.due_date}'. Expected ISO format (e.g., '2025-12-17T21:00:00') or 'YYYY-MM-DD HH:MM' (e.g., '2025-12-17 21:00')"
                    )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error parsing due_date '{payload.due_date}': {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid due_date format: '{payload.due_date}'. Error: {str(e)}"
        )

    # ☁️ STEP 1: Interpret user input as IST (Asia/Kolkata)
    # If due_dt is naive (no timezone), assume it's IST
    if due_dt.tzinfo is None:
        due_local = IST.localize(due_dt)  # "2025-12-16 21:00:00" → "2025-12-16 21:00:00 IST"
        logger.info(f"[TIME] Parsed as naive, localized to IST: {due_local.strftime('%Y-%m-%d %I:%M %p IST')}")
    else:
        # If it already has timezone, convert to IST first
        due_local = due_dt.astimezone(IST)
        logger.info(f"[TIME] Had timezone, converted to IST: {due_local.strftime('%Y-%m-%d %I:%M %p IST')}")
    
    # 🎯 CRITICAL CHECK: Is this really "2 minutes from now"?
    time_diff_minutes = (due_local - now_ist).total_seconds() / 60
    logger.info(f"[TIME] ⚡ Time difference: {time_diff_minutes:.2f} minutes from now")
    logger.info(f"[TIME] Expected for 'in 2 min': ~2.0 minutes")
    
    if abs(time_diff_minutes) > 24 * 60:  # More than 24 hours difference
        logger.warning(f"[TIME] ⚠️  SUSPICIOUS: Time difference is {time_diff_minutes:.1f} minutes (~{time_diff_minutes/60/24:.1f} days)")
        logger.warning(f"[TIME] ⚠️  This suggests LLM calculated wrong datetime!")
    
    # ☁️ STEP 2: Convert IST to UTC (Machine Time for Celery)
    # 9 PM IST → 3:30 PM UTC (example)
    due_utc = due_local.astimezone(UTC)
    
    # For MongoDB storage (naive datetime for consistency)
    now_utc = datetime.now(timezone.utc)
    now_naive = now_utc.replace(tzinfo=None)
    due_dt_naive = due_utc.replace(tzinfo=None)
    
    # ✅ Check if the due date has already passed
    if due_dt_naive < now_naive:
        raise HTTPException(
            status_code=400, 
            detail="time_passed",  # Special error code for frontend
            headers={"X-Error-Type": "TIME_PASSED"}
        )
    
    # 🚀 Part 20: Idempotency check (prevents retry storms, double-clicks)
    start_time = time.time()
    is_duplicate, cached_result = await is_duplicate_task(
        user_id=str(user_id),
        description=payload.description,
        due_date=payload.due_date
    )
    
    if is_duplicate and cached_result:
        latency_ms = (time.time() - start_time) * 1000
        
        # 🚀 Part 19: Log duplicate prevention
        log_task_operation(
            user_id=str(user_id),
            intent="create_duplicate_prevented",
            latency_ms=latency_ms,
            task_id=cached_result.get("task_id"),
            success=True
        )
        
        # Return cached task to prevent duplicate
        existing_task = await tasks_collection.find_one({"_id": ObjectId(cached_result["task_id"])})
        if existing_task:
            return TaskResponse(
                task_id=str(existing_task["_id"]),
                description=existing_task["description"],
                due_date=existing_task["due_date"],
                status=existing_task["status"],
                email_status=existing_task.get("email_status"),
                email_retry_count=existing_task.get("email_retry_count"),
                email_last_error=existing_task.get("email_last_error"),
                email_sent_at=existing_task.get("email_sent_at"),
                recurrence=existing_task.get("recurrence"),
                confirmation_message="✅ This reminder already exists! No duplicate created.",
            )
    
    # ✅ Additional check: MongoDB duplicate check (backup, in case Redis fails)
    time_buffer = timedelta(minutes=5)
    existing_task = await tasks_collection.find_one({
        "userId": user_id,
        "description": payload.description,
        "status": {"$in": ["pending", "active"]},
        "due_date": {
            "$gte": due_dt_naive - time_buffer,
            "$lte": due_dt_naive + time_buffer
        }
    })

    if existing_task:
        latency_ms = (time.time() - start_time) * 1000
        
        # 🚀 Part 19: Log duplicate prevention (DB check)
        log_task_operation(
            user_id=str(user_id),
            intent="create_duplicate_db_check",
            latency_ms=latency_ms,
            task_id=str(existing_task["_id"]),
            success=True
        )
        
        # Return existing task instead of creating duplicate
        return TaskResponse(
            task_id=str(existing_task["_id"]),
            description=existing_task["description"],
            due_date=existing_task["due_date"],
            status=existing_task["status"],
            email_status=existing_task.get("email_status"),
            email_retry_count=existing_task.get("email_retry_count"),
            email_last_error=existing_task.get("email_last_error"),
            email_sent_at=existing_task.get("email_sent_at"),
            recurrence=existing_task.get("recurrence"),
            confirmation_message="✅ This reminder already exists! No duplicate created.",
        )
    
    # ☁️ Store both UTC (for sorting/debugging) and display time (for email)
    # Source of Truth: Store UTC for machine operations, display_time for human-readable email
    doc = {
        "userId": user_id,
        "description": payload.description,
        "due_date": due_dt_naive,  # Naive UTC for MongoDB queries
        "due_date_utc": due_utc,    # UTC datetime object (for debugging)
        "display_time": f"{due_local.strftime('%Y-%m-%d %I:%M %p')} IST",  # Human-readable for email
        "status": "pending",
        "email_status": "queued",
        "email_retry_count": 0,
        "email_last_error": None,
        "email_sent_at": None,
        "created_at": now_naive,
        "updated_at": now_naive,
        "user_email": current_user.email,
        "user_name": current_user.name or current_user.email.split("@")[0],
        "recurrence": payload.recurrence or None,
    }

    # ☁️ Save task to MongoDB
    try:
        result = await tasks_collection.insert_one(doc)
        task_id = str(result.inserted_id)
        logger.info(f"✅ Task saved to MongoDB: {task_id} for user {user_id}")
        print(f"✅ Task saved to MongoDB with ID: {task_id}")
        
        # Verify task was saved correctly
        saved_task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
        if not saved_task:
            raise Exception("Task was not found after insertion - database write may have failed")
        logger.info(f"✅ Task verification passed: {task_id}")
        
    except Exception as db_error:
        logger.error(f"❌ Failed to save task to MongoDB: {db_error}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save task to database: {str(db_error)}"
        )
    
    limit_warning: Optional[str] = None

    # 🚀 Part 20: Mark task as created (idempotency)
    await mark_task_created(
        user_id=str(user_id),
        description=payload.description,
        due_date=payload.due_date,
        task_id=task_id
    )

    # 🚀 Part 10: Invalidate cache on CREATE
    await cache_service.invalidate_tasks(user_id)
    
    # 🚀 Part 19: Log task creation
    latency_ms = (time.time() - start_time) * 1000
    log_task_operation(
        user_id=str(user_id),
        intent="create",
        latency_ms=latency_ms,
        task_id=task_id,
        success=True
    )

    # ☁️ CLOUD-NATIVE: Schedule reminder using Celery with eta (Estimated Time of Arrival)
    # Celery lives on Cloud Server (UTC clock), so we pass UTC datetime object
    # User said "9 PM IST" → We calculated "3:30 PM UTC" → Celery waits until that UTC time
    try:
        from app.tasks.email_tasks import send_reminder_email_task
        from app.core.celery_app import CELERY_AVAILABLE, celery_app
        
        # Check if Celery is available and properly initialized
        if not CELERY_AVAILABLE or celery_app is None:
            raise ImportError("Celery is not available. Please install: pip install 'celery[redis]>=5.3.0'")
        
        # Check if task function has apply_async method (is a Celery task)
        if not hasattr(send_reminder_email_task, 'apply_async'):
            raise AttributeError("send_reminder_email_task is not a Celery task. Celery may not be properly initialized.")
        
        # ☁️ CRITICAL: Pass UTC datetime object (not naive, not IST)
        # Celery requires timezone-aware datetime in UTC for eta parameter
        # Ensure due_utc is timezone-aware UTC datetime
        if due_utc.tzinfo is None:
            # If naive, assume it's already UTC
            due_utc = due_utc.replace(tzinfo=timezone.utc)
        elif due_utc.tzinfo != timezone.utc:
            # Convert to UTC if not already
            due_utc = due_utc.astimezone(timezone.utc)
        
        # Schedule task with Celery
        result = send_reminder_email_task.apply_async(
            args=[task_id],
            eta=due_utc  # UTC datetime object - Celery will wake up at this exact UTC time
        )
        
        # Log scheduling details
        time_until_execution = (due_utc - datetime.now(timezone.utc)).total_seconds()
        logger.info(f"✅ [Cloud] Task scheduled on Celery")
        logger.info(f"   Task ID: {task_id}")
        logger.info(f"   Celery Task ID: {result.id}")
        logger.info(f"   IST Time: {due_local.strftime('%Y-%m-%d %I:%M %p %Z')}")
        logger.info(f"   UTC Time: {due_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"   Time until execution: {time_until_execution:.0f} seconds ({time_until_execution/60:.1f} minutes)")
        print(f"✅ [Cloud] Task scheduled on Celery")
        print(f"   Task ID: {task_id}")
        print(f"   Celery Task ID: {result.id}")
        print(f"   IST Time: {due_local.strftime('%Y-%m-%d %I:%M %p %Z')}")
        print(f"   UTC Time: {due_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Time until execution: {time_until_execution:.0f} seconds ({time_until_execution/60:.1f} minutes)")
    except ImportError as import_error:
        # Celery not installed - task saved but email won't be sent
        error_msg = str(import_error)
        logger.error(f"❌ Celery not available: {error_msg}")
        logger.error("📦 Installation: pip install 'celery[redis]>=5.3.0'")
        logger.error("🚀 Start worker: celery -A app.core.celery_app worker --loglevel=info --queues=email,default")
        print(f"❌ Celery not available: {error_msg}")
        print("📦 To enable email reminders, install Celery:")
        print("   pip install 'celery[redis]>=5.3.0'")
        print("🚀 Then start Celery worker:")
        print("   celery -A app.core.celery_app worker --loglevel=info --queues=email,default")
        limit_warning = "⚠️ Task saved but Celery is not available. Install Celery and start worker to enable email reminders."
    except AttributeError as attr_error:
        # Celery app not properly initialized or task not registered
        logger.error(f"❌ Celery task not available: {attr_error}")
        print(f"❌ Celery task not available: {attr_error}")
        print("📦 Make sure Celery is installed and worker is running")
        limit_warning = "⚠️ Task saved but Celery task is not available. Please check Celery installation and worker."
    except Exception as e:
        logger.error(f"⚠️ Celery scheduling error: {e}")
        print(f"⚠️ Celery scheduling error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        limit_warning = "⚠️ Task saved but email scheduling failed. Please check Celery worker."
    
    # 📝 LOG: Task Created
    print("\n" + "="*70)
    print("✅ TASK CREATED SUCCESSFULLY")
    print("="*70)
    print(f"📋 Task ID: {task_id}")
    print(f"👤 User: {current_user.name or current_user.email}")
    print(f"📧 Email: {current_user.email}")
    print(f"📝 Description: {payload.description}")
    print(f"⏰ Due Date (IST): {due_local.strftime('%Y-%m-%d %I:%M %p %Z')}")
    print(f"⏰ Due Date (UTC): {due_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"🔔 Status: pending")
    if payload.recurrence:
        print(f"🔄 Recurrence: {payload.recurrence.get('type', 'N/A')}")
    print("="*70 + "\n")

    # Build a clear confirmation message for chat/frontend
    # Use due_local for display (shows IST time to user)
    pretty_time = due_local.strftime("%A, %b %d at %I:%M %p IST") if due_local else "unspecified time"
    if payload.recurrence:
        freq = payload.recurrence.get("type", "recurring")
        if freq == "daily":
            freq_str = "every day"
        elif freq == "weekday":
            freq_str = "every weekday"
        elif freq == "interval_hours":
            freq_str = f"every {payload.recurrence.get('interval_hours', 1)} hours"
        elif freq == "monthly_day":
            freq_str = "on the same day every month"
        else:
            freq_str = "on a recurring schedule"
        confirmation = (
            f"✅ Done! I've scheduled a recurring reminder to {payload.description} {freq_str}, "
            f"next at {pretty_time}. I'll notify you via email at your registered address 📧."
        )
    else:
        confirmation = (
            f"✅ Done! I've scheduled a reminder to {payload.description} at {pretty_time}. "
            "I'll notify you via email at your registered address 📧."
        )

    # ☁️ Return due_date in a format frontend can use
    # Use due_dt (the original parsed datetime) for response
    # Frontend expects datetime object or ISO string
    return TaskResponse(
        task_id=task_id,
        description=payload.description,
        due_date=due_dt,  # Original parsed datetime (may be naive or timezone-aware)
        status="pending",
        email_status="queued",
        email_retry_count=0,
        email_last_error=None,
        email_sent_at=None,
        recurrence=payload.recurrence or None,
        confirmation_message=f"{confirmation} {limit_warning or ''}".strip(),
    )


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    status: Optional[Literal["pending", "completed"]] = Query(default=None),
    current_user: User = Depends(get_current_user_from_session),
):
    """
    Returns tasks for the current user, optionally filtered by status.
    ✨ OPTIMIZED: Uses projections + Redis caching for maximum performance.
    🚀 Part 9: MongoDB projections (smaller payloads)
    🚀 Part 10: Redis caching (avoid unnecessary DB queries)
    """
    user_id = current_user.user_id

    # 🚀 Part 10: Try cache first
    cached_tasks = await cache_service.get_tasks(user_id, status)
    if cached_tasks is not None:
        # Cache hit - deserialize and return
        return [
            TaskResponse(
                task_id=t["task_id"],
                description=t["description"],
                due_date=datetime.fromisoformat(t["due_date"]) if t.get("due_date") else None,
                status=t["status"],
                email_status=t.get("email_status"),
                email_retry_count=t.get("email_retry_count"),
                email_last_error=t.get("email_last_error"),
                email_sent_at=datetime.fromisoformat(t["email_sent_at"]) if t.get("email_sent_at") else None,
            )
            for t in cached_tasks
        ]

    # Cache miss - fetch from database
    query: dict = {"userId": user_id}
    if status:
        query["status"] = status

    # 🚀 Part 9: Projection - fetch only required fields (smaller payloads)
    # ☁️ MongoDB doesn't allow mixing inclusion (1) and exclusion (0) in same projection
    # Use inclusion-only: specify only fields we want (recurrence and userId excluded by omission)
    projection = {
        "_id": 1,
        "description": 1,
        "due_date": 1,
        "status": 1,
        "email_status": 1,
        "email_retry_count": 1,
        "email_last_error": 1,
        "email_sent_at": 1,
        # Note: recurrence and userId are excluded by not including them
    }

    cursor = tasks_collection.find(query, projection).sort("due_date", 1)
    tasks: list[TaskResponse] = []
    tasks_for_cache = []  # Serializable format for cache

    async for t in cursor:
        task_response = TaskResponse(
            task_id=str(t.get("_id")),
            description=t.get("description", ""),
            due_date=t.get("due_date"),
            status=t.get("status", "pending"),
            email_status=t.get("email_status"),
            email_retry_count=t.get("email_retry_count"),
            email_last_error=t.get("email_last_error"),
            email_sent_at=t.get("email_sent_at"),
        )
        tasks.append(task_response)
        
        # Prepare cache-friendly version
        tasks_for_cache.append({
            "task_id": str(t.get("_id")),
            "description": t.get("description", ""),
            "due_date": t.get("due_date").isoformat() if t.get("due_date") else None,
            "status": t.get("status", "pending"),
            "email_status": t.get("email_status"),
            "email_retry_count": t.get("email_retry_count"),
            "email_last_error": t.get("email_last_error"),
            "email_sent_at": t.get("email_sent_at").isoformat() if t.get("email_sent_at") else None,
        })

    # 🚀 Part 10: Cache for future requests
    await cache_service.set_tasks(user_id, tasks_for_cache, status)

    return tasks


@router.post("/update", response_model=TaskResponse)
async def update_task(
    payload: UpdateTaskRequest,
    current_user: User = Depends(get_current_user_from_session),
):
    """Update an existing task's time/description/recurrence after chat confirmation."""
    user_id = current_user.user_id

    try:
        obj_id = ObjectId(payload.task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid task_id")

    # Fetch task and verify ownership
    task = await tasks_collection.find_one({"_id": obj_id, "userId": user_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    updates: dict = {}
    if payload.description:
        updates["description"] = payload.description

    if payload.due_date:
        try:
            try:
                due_dt = datetime.fromisoformat(payload.due_date)
            except ValueError:
                due_dt = datetime.strptime(payload.due_date, "%Y-%m-%d %H:%M")
            local_tz = ZoneInfo("Asia/Kolkata")
            due_local = due_dt if due_dt.tzinfo else due_dt.replace(tzinfo=local_tz)
            updates["due_date"] = due_local.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid due_date format")
    else:
        due_dt = task.get("due_date")

    if payload.recurrence is not None:
        updates["recurrence"] = payload.recurrence

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

    await tasks_collection.update_one({"_id": obj_id}, {"$set": updates})

    # 🚀 Part 10: Invalidate cache on UPDATE
    await cache_service.invalidate_tasks(user_id)

    # Re-fetch updated task
    updated = await tasks_collection.find_one({"_id": obj_id})
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to load updated task")

    desc = updated.get("description", "")
    due = updated.get("due_date")
    if isinstance(due, str):
        try:
            due_dt = datetime.fromisoformat(due)
        except Exception:
            due_dt = None
    else:
        due_dt = due
    pretty_time = (
        due_dt.strftime("%A, %b %d at %I:%M %p") if isinstance(due_dt, datetime) else "unspecified time"
    )

    recurrence = updated.get("recurrence")
    if recurrence:
        freq = recurrence.get("type", "recurring")
        if freq == "daily":
            freq_str = "every day"
        elif freq == "weekday":
            freq_str = "every weekday"
        elif freq == "interval_hours":
            freq_str = f"every {recurrence.get('interval_hours', 1)} hours"
        elif freq == "monthly_day":
            freq_str = "on the same day every month"
        else:
            freq_str = "on a recurring schedule"
        confirmation = (
            f"🔄 Updated your recurring reminder to **{desc}** {freq_str}, next at {pretty_time}."
        )
    else:
        confirmation = (
            f"🔄 Updated your reminder to **{desc}** at {pretty_time}."
        )

    return TaskResponse(
        task_id=str(updated["_id"]),
        description=desc,
        due_date=due_dt,
        status=updated.get("status", "pending"),
        email_status=updated.get("email_status"),
        email_retry_count=updated.get("email_retry_count"),
        email_last_error=updated.get("email_last_error"),
        email_sent_at=updated.get("email_sent_at"),
        recurrence=recurrence,
        confirmation_message=confirmation,
    )


@router.post("/cancel", response_model=TaskResponse)
async def cancel_task(
    payload: CancelTaskRequest,
    current_user: User = Depends(get_current_user_from_session),
):
    """Cancel a task after chat confirmation."""
    user_id = current_user.user_id

    try:
        obj_id = ObjectId(payload.task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid task_id")

    task = await tasks_collection.find_one({"_id": obj_id, "userId": user_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    await tasks_collection.update_one(
        {"_id": obj_id},
        {"$set": {"status": "cancelled", "updated_at": now}},
    )
    
    # 🚀 Part 10: Invalidate cache on CANCEL
    await cache_service.invalidate_tasks(user_id)
    
    # Remove any scheduled email
    try:
        await remove_scheduled_email(str(obj_id))
    except Exception:
        pass

    desc = task.get("description", "")
    due = task.get("due_date")
    if isinstance(due, str):
        try:
            due_dt = datetime.fromisoformat(due)
        except Exception:
            due_dt = None
    else:
        due_dt = due
    pretty_time = (
        due_dt.strftime("%A, %b %d at %I:%M %p") if isinstance(due_dt, datetime) else "its scheduled time"
    )

    confirmation = (
        f"⛔ Stopped your reminder for **{desc}** that was scheduled for {pretty_time}."
    )

    return TaskResponse(
        task_id=str(task["_id"]),
        description=desc,
        due_date=due_dt,
        status="cancelled",
        recurrence=task.get("recurrence"),
        confirmation_message=confirmation,
    )


@router.post("/test-email/{task_id}")
async def test_task_email(
    task_id: str,
    current_user: User = Depends(get_current_user_from_session),
):
    """
    Test endpoint to manually trigger email notification for a specific task.
    Useful for testing email configuration and delivery.
    """
    try:
        obj_id = ObjectId(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid task_id format")

    # Fetch task
    task = await tasks_collection.find_one({"_id": obj_id, "userId": current_user.user_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Import email service
    from app.services.email_service import send_professional_email

    try:
        # Send test email
        await send_professional_email(task)
        
        # Log the test
        now = datetime.utcnow()
        await tasks_collection.update_one(
            {"_id": obj_id},
            {
                "$set": {
                    "test_email_sent_at": now,
                    "last_email_test": now,
                }
            }
        )
        
        return {
            "success": True,
            "message": f"✅ Test email sent to {task.get('user_email')}",
            "task_id": task_id,
            "description": task.get("description"),
            "recipient": task.get("user_email"),
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Failed to send test email: {str(e)}",
            "task_id": task_id,
            "error": str(e),
        }
