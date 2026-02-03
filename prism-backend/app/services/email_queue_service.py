import json
import time
from datetime import datetime, timezone

from app.db.redis_client import redis_client, EMAIL_HIGH_PRIORITY_QUEUE, EMAIL_SCHEDULED_QUEUE, EMAIL_DAILY_LIMIT_KEY_TEMPLATE
from app.config import settings

# Backwards-compatible aliases matching product brief
QUEUE_HIGH = EMAIL_HIGH_PRIORITY_QUEUE
QUEUE_SCHEDULED = EMAIL_SCHEDULED_QUEUE
LIMIT_PREFIX = "limit:email:"


async def check_and_increment_limit(user_id: str) -> bool:
    """
    ATOMIC rate limiter for task emails (10/day).
    Returns True if user is under the limit and increments the counter.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    key = EMAIL_DAILY_LIMIT_KEY_TEMPLATE.format(user_id=user_id, date=today)

    current_count = await redis_client.incr(key)
    if current_count == 1:
        await redis_client.expire(key, 86400)

    if current_count > settings.MAX_DAILY_TASK_EMAILS:
        return False

    return True


async def enqueue_otp(email: str, otp_code: str):
    """
    🚀 LANE 1: HIGH PRIORITY (Express)
    Bypasses rate limits. Goes straight to the list.
    """
    payload = {
        "type": "otp",
        "to_email": email,
        "data": {"otp": otp_code},
        "created_at": time.time(),
    }
    await redis_client.lpush(QUEUE_HIGH, json.dumps(payload))
    print(f"🚀 Enqueued OTP for {email}")


async def schedule_task_reminder(task_id: str, user_id: str, due_timestamp: float):
    """
    🐢 LANE 2: SCHEDULED (Task Reminders)
    Checked against rate limit first. Adds to ZSet.
    """
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
    
    is_allowed = await check_and_increment_limit(user_id)
    if not is_allowed:
        raise ValueError("Daily email limit reached.")

    await redis_client.zadd(QUEUE_SCHEDULED, {task_id: due_timestamp})

    # 🚀 PRO LEVEL UPGRADE: Dispatch to Celery if available for EXACT time execution
    try:
        from app.core.celery_app import celery_app
        if celery_app:
            # eta expects a datetime object (UTC preferred by Celery internal)
            # due_timestamp is float seconds.
            dt_eta = datetime.fromtimestamp(due_timestamp, timezone.utc)
            dt_ist = dt_eta.astimezone(IST)
            time_display = dt_ist.strftime("%I:%M %p IST").lstrip("0")
            
            celery_app.send_task(
                "prism_tasks.send_reminder_email",
                args=[task_id],
                eta=dt_eta,
                queue="email"
            )
            print(f"📧 Email reminder scheduled for {time_display}")
    except Exception as e:
        print(f"⚠️ Celery dispatch failed (fallback to Redis worker used): {e}")


async def remove_scheduled_email(task_id: str):
    """
    If user deletes/cancels a task, remove it from the email queue.
    """
    await redis_client.zrem(QUEUE_SCHEDULED, task_id)

