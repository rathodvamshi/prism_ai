import asyncio
from datetime import datetime, timedelta
from typing import Optional
from calendar import monthrange

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.mongo_client import tasks_collection
from app.services.email_service import send_professional_email
from app.services.pending_memory_service import sync_pending_graph_memories

scheduler = AsyncIOScheduler()

TASK_RUNNER_JOB_ID = "task_runner_next"


async def _fetch_next_task():
    """Get the next pending task ordered by due_date."""
    return await tasks_collection.find_one(
        {"status": "pending", "due_date": {"$ne": None}},
        sort=[("due_date", 1)],
    )


async def _execute_task(task: dict):
    """Send notification email and update or reschedule the task."""
    now = datetime.utcnow()
    task_id = task.get('_id')
    description = task.get('description', 'Task')
    user_email = task.get('user_email')
    
    # 🚀 Part 15: Prevent duplicate execution - check status BEFORE sending email
    current_task = await tasks_collection.find_one({"_id": task_id})
    if not current_task or current_task.get("status") != "pending":
        print(f"⚠️ Task {task_id} is not pending (status: {current_task.get('status') if current_task else 'not found'}), skipping execution")
        return
    
    print(f"🔔 Executing task {task_id}: {description}")
    print(f"📧 Sending email to: {user_email}")
    
    # Send email notification
    email_success = False
    try:
        await send_professional_email(task)
        email_success = True
        print(f"✅ Email sent successfully for task {task_id}")
    except Exception as e:
        print(f"❌ Email send failed for task {task_id}: {e}")
        # Log error but continue with task completion
        await tasks_collection.update_one(
            {"_id": task_id},
            {"$set": {"email_error": str(e), "email_sent": False, "updated_at": now}},
        )
    
    # If task has a recurrence rule and is still active, compute the next run.
    recurrence = task.get("recurrence") or {}
    if recurrence and task.get("status") == "pending":
        next_due = _compute_next_due_date(task.get("due_date"), recurrence)
        if next_due:
            # 🚀 Part 15: Atomic update - only reschedule if status is still "pending"
            result = await tasks_collection.update_one(
                {"_id": task_id, "status": "pending"},  # Atomic check
                {
                    "$set": {
                        "due_date": next_due,
                        "updated_at": now,
                        "email_sent": email_success,
                        "last_notification_at": now,
                    }
                },
            )
            if result.modified_count > 0:
                print(f"♻️ Rescheduled recurring task {task_id} for {next_due}")
            else:
                print(f"⚠️ Task {task_id} was already modified (prevented duplicate reschedule)")
            return

    # One-time tasks, or recurrence could not be computed → mark completed.
    # 🚀 Part 15: Atomic update - only update if status is still "pending"
    result = await tasks_collection.update_one(
        {"_id": task_id, "status": "pending"},  # Atomic check: only update if still pending
        {
            "$set": {
                "status": "completed",
                "completed_at": now,
                "updated_at": now,
                "email_sent": email_success,
                "notified_at": now,
            }
        },
    )
    if result.modified_count > 0:
        print(f"✅ Task {task_id} marked as completed")
    else:
        print(f"⚠️ Task {task_id} was already modified (prevented duplicate completion)")


def _compute_next_due_date(current_due, recurrence: dict) -> Optional[datetime]:
    """Compute the next due_date for a recurring task based on server time."""
    if not isinstance(current_due, datetime):
        return None
    rule_type = recurrence.get("type")

    if rule_type == "daily":
        return current_due + timedelta(days=1)

    if rule_type == "weekday":
        # Move to next weekday (Mon–Fri)
        next_dt = current_due + timedelta(days=1)
        while next_dt.weekday() >= 5:  # 5=Sat, 6=Sun
            next_dt += timedelta(days=1)
        return next_dt

    if rule_type == "interval_hours":
        hours = int(recurrence.get("interval_hours", 1))
        return current_due + timedelta(hours=hours)

    if rule_type == "monthly_day":
        # Move to next month and clamp the requested day to the valid range.
        requested_day = int(recurrence.get("day_of_month", 1))
        year = current_due.year
        month = current_due.month + 1
        if month > 12:
            month = 1
            year += 1
        days_in_month = monthrange(year, month)[1]
        day = max(1, min(requested_day, days_in_month))
        try:
            return current_due.replace(year=year, month=month, day=day)
        except ValueError:
            return None

    return None


async def _run_and_reschedule(task_id):
    # Reload to ensure status is still pending
    task = await tasks_collection.find_one({"_id": task_id})
    if not task or task.get("status") != "pending":
        print(f"⚠️  Task {task_id} no longer pending, skipping...")
        await schedule_next_task()
        return
    await _execute_task(task)
    await schedule_next_task()


async def schedule_next_task():
    """
    Optimized scheduler:
    - Finds the next pending task instantly
    - Sends email 3 minutes before due time
    - No busy-waiting, efficient event-driven execution
    """
    # Remove any existing job to avoid duplicates (fast operation)
    try:
        job = scheduler.get_job(TASK_RUNNER_JOB_ID)
        if job:
            scheduler.remove_job(TASK_RUNNER_JOB_ID)
    except Exception:
        pass

    next_task = await _fetch_next_task()
    if not next_task:
        # Shorter idle check for faster response (5 min instead of 10)
        run_at = datetime.utcnow() + timedelta(minutes=5)
        scheduler.add_job(
            schedule_next_task,
            trigger="date",
            run_date=run_at,
            id=TASK_RUNNER_JOB_ID,
            replace_existing=True,
        )
        return

    due_date = next_task.get("due_date")
    if not isinstance(due_date, datetime):
        # Skip invalid and move on
        await tasks_collection.update_one(
            {"_id": next_task["_id"]}, {"$set": {"status": "invalid"}}
        )
        await schedule_next_task()
        return

    # Send email 3 minutes BEFORE due time for better UX
    now = datetime.utcnow()
    time_until_due = (due_date - now).total_seconds()
    notification_advance_time = 180  # 3 minutes = 180 seconds
    
    # Calculate when to send the email (3 min before due time)
    time_until_notification = time_until_due - notification_advance_time
    
    if time_until_notification <= 0:  # Already time to notify or overdue
        # Execute immediately - no delay
        print(f"⚡ Sending notification NOW for task {next_task.get('_id')} (due in {time_until_due:.0f}s)")
        
        # Execute immediately in current event loop
        import asyncio
        asyncio.create_task(_run_and_reschedule(next_task["_id"]))
    else:
        # Schedule to wake up 3 minutes before due time
        wake_time = due_date - timedelta(seconds=notification_advance_time)
        print(f"📅 Scheduler armed: notify at {wake_time.strftime('%H:%M:%S')} (3 min before {due_date.strftime('%H:%M:%S')})")
        
        scheduler.add_job(
            _run_and_reschedule,
            trigger="date",
            run_date=wake_time,
            id=TASK_RUNNER_JOB_ID,
            replace_existing=True,
            args=[next_task["_id"]],
        )


def start_scheduler():
    # Kick off task scheduler (sleep-based, no busy loop)
    scheduler.add_job(schedule_next_task, trigger="date", run_date=datetime.utcnow())

    # 🧠 Background auto-healing for pending memory → Neo4j
    scheduler.add_job(
        sync_pending_graph_memories,
        "interval",
        minutes=3,
        id="pending_memory_sync",
        replace_existing=True,
    )
    scheduler.start()