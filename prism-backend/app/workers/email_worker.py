import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.db.redis_client import (
    redis_client,
    EMAIL_HIGH_PRIORITY_QUEUE,
    EMAIL_SCHEDULED_QUEUE,
    EMAIL_DLQ,
    EMAIL_LOCK_KEY_TEMPLATE,
)
from app.db.mongo_client import tasks_collection
from app.services.email_service import send_otp_email_direct
from app.config import settings

# Backwards-compatible aliases matching the product brief
QUEUE_HIGH = EMAIL_HIGH_PRIORITY_QUEUE
QUEUE_SCHEDULED = EMAIL_SCHEDULED_QUEUE
QUEUE_DLQ = EMAIL_DLQ
LOCK_PREFIX = EMAIL_LOCK_KEY_TEMPLATE.replace("{task_id}", "")


async def acquire_lock(lock_id: str, ttl: int = 300) -> bool:
    """
    Ensure we don't process the same task twice concurrently.
    Sets a key that expires in 5 minutes.
    """
    key = f"{LOCK_PREFIX}{lock_id}"
    return await redis_client.set(key, "LOCKED", ex=ttl, nx=True)


async def release_lock(lock_id: str):
    await redis_client.delete(f"{LOCK_PREFIX}{lock_id}")


async def handle_retry(task_id: str, current_retries: int, error_msg: str):
    """
    Calculates backoff and re-schedules or moves to DLQ.
    """
    if current_retries >= len(settings.EMAIL_RETRY_DELAYS):
        print(f"💀 Task {task_id} failed permanently. Moving to DLQ.")
        await redis_client.lpush(QUEUE_DLQ, json.dumps({"task_id": task_id, "error": error_msg}))

        await tasks_collection.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {"email_status": "failed", "email_last_error": error_msg}},
        )
        return

    delay = settings.EMAIL_RETRY_DELAYS[current_retries]
    next_attempt = datetime.now(timezone.utc).timestamp() + delay

    print(f"🔄 Retrying Task {task_id} in {delay}s (Attempt {current_retries + 1})")
    await redis_client.zadd(QUEUE_SCHEDULED, {task_id: next_attempt})

    await tasks_collection.update_one(
        {"_id": ObjectId(task_id)},
        {
            "$set": {
                "email_status": "retrying",
                "email_retry_count": current_retries + 1,
                "email_last_error": error_msg,
            }
        },
    )


async def process_otp(payload: dict):
    """
    🚀 LANE 1 PROCESSOR
    """
    email = payload.get("to_email")
    otp = payload.get("data", {}).get("otp")
    print(f"🚀 Sending OTP to {email}")

    try:
        await send_otp_email_direct(email, otp)
    except Exception as e:
        print(f"❌ OTP Failed: {e}")


async def process_task(task_id: str):
    """
    🐢 LANE 2 PROCESSOR
    """
    if not await acquire_lock(task_id):
        return

    try:
        oid = ObjectId(task_id)
    except Exception:
        oid = task_id

    try:
        task = await tasks_collection.find_one({"_id": oid})

        if not task:
            print(f"⚠️ Task {task_id} not found in DB. Removing from queue.")
            await redis_client.zrem(QUEUE_SCHEDULED, task_id)
            return

        # 🚀 Part 15: Prevent duplicate execution - check status BEFORE sending email
        if task.get("status") != "pending":
            print(f"⚠️ Task {task_id} is not pending (status: {task.get('status')}). Skipping.")
            await redis_client.zrem(QUEUE_SCHEDULED, task_id)
            return

        if task.get("email_status") == "sent":
            print(f"⚠️ Task {task_id} already sent. Skipping.")
            await redis_client.zrem(QUEUE_SCHEDULED, task_id)
            return

        print(f"📧 Scheduling email via Celery for: {task.get('description')}")
        
        # Use Celery task for consistency (immediate execution)
        try:
            from app.tasks.email_tasks import send_reminder_email_task
            from app.core.celery_app import CELERY_AVAILABLE, celery_app
            
            if CELERY_AVAILABLE and celery_app:
                # Send immediately via Celery
                celery_app.send_task(
                    "prism_tasks.send_reminder_email",
                    args=[task_id],
                    queue="email"
                )
                print(f"✅ Email task queued for {task_id}")
                
                # Mark as email_queued (Celery will update to sent when complete)
                await tasks_collection.update_one(
                    {"_id": task["_id"], "status": "pending"},
                    {
                        "$set": {
                            "email_status": "queued",
                            "email_queued_at": datetime.now(timezone.utc),
                            # Don't mark as completed yet - let Celery do that
                        }
                    },
                )
                
            else:
                # Fallback to direct sending if Celery unavailable
                from app.services.email_service import send_professional_email
                await send_professional_email(task)
                
                # Mark as completed immediately for direct sending
                await tasks_collection.update_one(
                    {"_id": task["_id"], "status": "pending"},
                    {
                        "$set": {
                            "email_status": "sent",
                            "email_sent_at": datetime.now(timezone.utc),
                            "status": "completed",
                        }
                    },
                )
                
        except Exception as e:
            print(f"❌ Email processing failed for {task_id}: {e}")
            # Mark as failed
            await tasks_collection.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "email_status": "failed",
                        "email_error": str(e),
                        "status": "failed",
                        "updated_at": datetime.now(timezone.utc)
                    }
                },
            )

        if result.modified_count > 0:
            print(f"✅ Task {task_id} marked as sent")
        else:
            print(f"⚠️ Task {task_id} was already modified (prevented duplicate send)")

        await redis_client.zrem(QUEUE_SCHEDULED, task_id)

    except Exception as e:
        print(f"❌ Error processing task {task_id}: {e}")
        await handle_retry(task_id, task.get("email_retry_count", 0) if task else 0, str(e))

    finally:
        await release_lock(task_id)


async def start_worker():
    print("👷 Email Worker Started...")
    while True:
        try:
            otp_raw = await redis_client.rpop(QUEUE_HIGH)
            if otp_raw:
                await process_otp(json.loads(otp_raw))
                continue

            now_ts = datetime.now(timezone.utc).timestamp()
            due_tasks = await redis_client.zrangebyscore(
                QUEUE_SCHEDULED, "0", str(now_ts), start=0, num=1
            )

            if due_tasks:
                task_id = due_tasks[0]
                await process_task(task_id)
            else:
                await asyncio.sleep(1)

        except Exception as e:
            print(f"💥 Worker Loop Error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(start_worker())

