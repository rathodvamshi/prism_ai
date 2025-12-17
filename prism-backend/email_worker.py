"""
⚡ EMAIL WORKER - Production-Ready Background Email Processor
Handles all email scheduling and sending (NEVER from API server)

Two-Phase Scheduling:
- PHASE 1 (T-2min): PREPARE - Validate, build payload, warm connection
- PHASE 2 (T-0min): SEND - Actually send the email

Features:
✅ Redis queue-based
✅ Multi-API-key rotation
✅ Rate limiting
✅ Idempotency (no duplicates)
✅ Auto-recovery
✅ Proper error handling
"""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from bson import ObjectId

from app.config import settings
from app.db.mongo_client import tasks_collection
from app.db.redis_client import redis_client
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Multiple SendGrid API keys for rotation
SENDGRID_KEYS = [
    settings.SENDGRID_API_KEY,
    # Add more keys here if you have them:
    # settings.SENDGRID_API_KEY_2,
    # settings.SENDGRID_API_KEY_3,
]

# Rate limits
GLOBAL_RATE_LIMIT = 10  # emails per minute (across all keys)
PER_USER_DAILY_LIMIT = 20  # emails per user per day
PREPARE_ADVANCE_TIME = 120  # 2 minutes in seconds

# Redis keys
QUEUE_READY = "email:queue:ready"  # Tasks ready to prepare
QUEUE_SEND = "email:queue:send"    # Tasks ready to send
LOCK_PREFIX = "email:lock:"        # Idempotency locks
RATE_LIMIT_GLOBAL = "email:rate:global"
RATE_LIMIT_USER = "email:rate:user:"
SENDGRID_KEY_USAGE = "email:sendgrid:usage:"

# Worker state
worker_running = False

# Observability metrics
worker_metrics = {
    "start_time": None,
    "emails_prepared": 0,
    "emails_sent": 0,
    "emails_failed": 0,
    "last_prepare_check": None,
    "last_send_check": None,
    "prepare_loop_heartbeat": 0,
    "send_loop_heartbeat": 0,
    "retries_total": 0
}


# ============================================================================
# SENDGRID MULTI-KEY ROTATION
# ============================================================================

async def get_best_sendgrid_key() -> str:
    """
    Select SendGrid API key with lowest usage.
    Implements smart rotation to avoid hitting rate limits.
    """
    best_key = SENDGRID_KEYS[0]
    lowest_usage = float('inf')
    
    for key in SENDGRID_KEYS:
        if not key or key == "":
            continue
            
        usage_key = f"{SENDGRID_KEY_USAGE}{key[:10]}"
        try:
            usage = await redis_client.get(usage_key)
            usage_count = int(usage) if usage else 0
            
            if usage_count < lowest_usage:
                lowest_usage = usage_count
                best_key = key
        except Exception as e:
            print(f"⚠️  Error checking key usage: {e}")
            continue
    
    return best_key


async def increment_key_usage(api_key: str):
    """Track API key usage with daily reset"""
    usage_key = f"{SENDGRID_KEY_USAGE}{api_key[:10]}"
    try:
        await redis_client.incr(usage_key)
        await redis_client.expire(usage_key, 86400)  # Reset daily
    except Exception as e:
        print(f"⚠️  Error incrementing key usage: {e}")


# ============================================================================
# RATE LIMITING
# ============================================================================

async def check_global_rate_limit() -> bool:
    """
    Check if we can send email (global limit).
    Returns True if OK, False if rate limited.
    """
    try:
        current = await redis_client.get(RATE_LIMIT_GLOBAL)
        count = int(current) if current else 0
        
        if count >= GLOBAL_RATE_LIMIT:
            return False
        
        await redis_client.incr(RATE_LIMIT_GLOBAL)
        await redis_client.expire(RATE_LIMIT_GLOBAL, 60)  # Per minute
        return True
    except Exception as e:
        print(f"⚠️  Rate limit check failed: {e}")
        return True  # Fail open


async def check_user_rate_limit(user_id: str) -> bool:
    """
    Check if user can send more emails today.
    Returns True if OK, False if rate limited.
    """
    try:
        key = f"{RATE_LIMIT_USER}{user_id}"
        current = await redis_client.get(key)
        count = int(current) if current else 0
        
        if count >= PER_USER_DAILY_LIMIT:
            return False
        
        await redis_client.incr(key)
        await redis_client.expire(key, 86400)  # Daily reset
        return True
    except Exception as e:
        print(f"⚠️  User rate limit check failed: {e}")
        return True  # Fail open


# ============================================================================
# IDEMPOTENCY (NO DUPLICATES)
# ============================================================================

async def acquire_send_lock(task_id: str) -> bool:
    """
    Acquire lock to prevent duplicate sends.
    Returns True if lock acquired, False if already locked.
    """
    lock_key = f"{LOCK_PREFIX}{task_id}"
    try:
        # Try to set lock (NX = only if not exists)
        result = await redis_client.set(lock_key, "locked", ex=300, nx=True)
        return result is not None
    except Exception as e:
        print(f"⚠️  Lock acquisition failed: {e}")
        return False  # Fail safe - don't send if unsure


async def release_send_lock(task_id: str):
    """Release send lock"""
    lock_key = f"{LOCK_PREFIX}{task_id}"
    try:
        await redis_client.delete(lock_key)
    except Exception as e:
        print(f"⚠️  Lock release failed: {e}")


# ============================================================================
# EMAIL PREPARATION (PHASE 1)
# ============================================================================

async def prepare_email(task: Dict) -> bool:
    """
    PHASE 1: Prepare email 2 minutes before sending.
    - Validate data
    - Build SendGrid payload
    - Select API key
    - Cache everything
    
    Returns True if prepared successfully.
    """
    task_id = str(task.get('_id'))
    description = task.get('description', 'Reminder')
    user_email = task.get('user_email')
    user_id = task.get('user_id')
    due_date = task.get('due_date')
    
    # Make due_date timezone-aware if it's naive
    if due_date and due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
    
    print(f"\n🔧 PHASE 1: Preparing email for task {task_id}")
    print(f"   📝 Description: {description}")
    print(f"   📧 Recipient: {user_email}")
    
    try:
        # 1. Validate user rate limit
        if not await check_user_rate_limit(user_id):
            print(f"❌ User {user_id} hit daily rate limit ({PER_USER_DAILY_LIMIT}/day)")
            await tasks_collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {
                    "status": "failed",
                    "error": "User rate limit exceeded",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            return False
        
        # 2. Select best SendGrid API key
        api_key = await get_best_sendgrid_key()
        if not api_key or api_key == "":
            print(f"❌ No valid SendGrid API key available")
            return False
        
        # 3. Build email HTML (beautiful template)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 40px 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; text-align: center;">
                    <h1 style="margin: 0; color: white; font-size: 28px; font-weight: 600;">⏰ Reminder Alert</h1>
                </div>
                <div style="padding: 40px;">
                    <div style="background: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
                        <p style="margin: 0; color: #495057; font-size: 18px; font-weight: 500;">{description}</p>
                    </div>
                    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 8px; text-align: center;">
                        <p style="margin: 0; color: white; font-size: 16px; font-weight: 600;">
                            🕐 Scheduled for: {due_date.strftime('%B %d, %Y at %I:%M %p UTC') if due_date else 'Now'}
                        </p>
                    </div>
                </div>
                <div style="background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e9ecef;">
                    <p style="margin: 0 0 5px 0; color: #6c757d; font-size: 13px;">
                        Sent with 💜 by <strong>PRISM AI</strong>
                    </p>
                    <p style="margin: 0; color: #9ca3af; font-size: 11px;">
                        {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 4. Build SendGrid payload
        from_addr = getattr(settings, "SENDER_EMAIL", "noreply@prism.ai")
        payload = {
            "from_email": from_addr,
            "to_emails": user_email,
            "subject": f"⏰ Reminder: {description}",
            "html_content": html_content,
            "api_key": api_key,
            "task_id": task_id
        }
        
        # 5. Cache prepared payload in Redis
        cache_key = f"email:prepared:{task_id}"
        await redis_client.setex(
            cache_key,
            300,  # 5 minutes TTL
            json.dumps(payload)
        )
        
        # 6. Update task status
        await tasks_collection.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "status": "ready",
                "prepared_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        print(f"✅ Email prepared successfully for task {task_id}")
        print(f"   🔑 Using API key: {api_key[:10]}...")
        
        # Update metrics
        worker_metrics["emails_prepared"] += 1
        
        return True
        
    except Exception as e:
        print(f"❌ Preparation failed for task {task_id}: {e}")
        await tasks_collection.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "status": "failed",
                "error": f"Preparation error: {str(e)}",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return False


# ============================================================================
# EMAIL SENDING (PHASE 2)
# ============================================================================

async def send_prepared_email(task: Dict, retry_count: int = 0, max_retries: int = 3) -> bool:
    """
    PHASE 2: Send the prepared email at exact scheduled time.
    - Check idempotency
    - Check rate limits
    - Send via SendGrid
    - Handle retries
    
    Returns True if sent successfully.
    """
    task_id = str(task.get('_id'))
    
    print(f"\n📧 PHASE 2: Sending email for task {task_id}")
    
    try:
        # 1. Check if already sent (idempotency)
        current_status = task.get('status')
        if current_status == 'sent' or current_status == 'completed':
            print(f"⚠️  Task {task_id} already sent, skipping...")
            return True
        
        # 2. Acquire idempotency lock
        if not await acquire_send_lock(task_id):
            print(f"⚠️  Task {task_id} is locked (already processing), skipping...")
            return False
        
        # 3. Check global rate limit
        if not await check_global_rate_limit():
            print(f"⚠️  Global rate limit exceeded, requeueing task {task_id}")
            await release_send_lock(task_id)
            # Re-queue for later
            await redis_client.rpush(QUEUE_SEND, task_id)
            await asyncio.sleep(10)  # Wait before retry
            return False
        
        # 4. Load prepared payload from cache
        cache_key = f"email:prepared:{task_id}"
        payload_json = await redis_client.get(cache_key)
        
        if not payload_json:
            print(f"⚠️  No prepared payload found for task {task_id}, preparing now...")
            if not await prepare_email(task):
                await release_send_lock(task_id)
                return False
            payload_json = await redis_client.get(cache_key)
        
        payload = json.loads(payload_json)
        
        # 5. Send via SendGrid
        msg = Mail(
            from_email=payload['from_email'],
            to_emails=payload['to_emails'],
            subject=payload['subject'],
            html_content=payload['html_content']
        )
        
        sg = SendGridAPIClient(payload['api_key'])
        response = sg.send(msg)
        
        # 6. Check response
        if response.status_code in [200, 201, 202]:
            print(f"✅ Email sent successfully for task {task_id}")
            print(f"   SendGrid Response: {response.status_code}")
            
            # Increment key usage
            await increment_key_usage(payload['api_key'])
            
            # Update task status
            await tasks_collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {
                    "status": "sent",
                    "sent_at": datetime.now(timezone.utc),
                    "email_sent": True,
                    "notified_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            
            # Clean up
            await redis_client.delete(cache_key)
            await release_send_lock(task_id)
            
            # Update metrics
            worker_metrics["emails_sent"] += 1
            
            return True
        else:
            raise Exception(f"SendGrid returned {response.status_code}")
    
    except Exception as e:
        error_msg = f"SendGrid error (Attempt {retry_count + 1}/{max_retries}): {str(e)}"
        print(f"❌ {error_msg}")
        
        # Retry logic with exponential backoff
        if retry_count < max_retries:
            wait_time = (retry_count + 1) * 10  # 10s, 20s, 30s
            print(f"⏳ Retrying in {wait_time}s...")
            
            # Update metrics
            worker_metrics["retries_total"] += 1
            
            await asyncio.sleep(wait_time)
            await release_send_lock(task_id)  # Release before retry
            return await send_prepared_email(task, retry_count + 1, max_retries)
        else:
            # 🚨 ALERT: Log to failure tracking
            print(f"🚨 ALERT: Task {task_id} FAILED after {max_retries} retries")
            print(f"   Error: {error_msg}")
            print(f"   User: {task.get('user_email')}")
            print(f"   Time: {datetime.now(timezone.utc).isoformat()}")
            
            await tasks_collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {
                    "status": "failed",
                    "error": error_msg,
                    "email_sent": False,
                    "failed_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            await release_send_lock(task_id)
            
            # Update metrics
            worker_metrics["emails_failed"] += 1
            return False


# ============================================================================
# WORKER LOOPS
# ============================================================================

async def prepare_loop():
    """
    Background loop that prepares emails 2 minutes before send time.
    Runs continuously, checking for tasks that need preparation.
    """
    print("\n🔧 PREPARE LOOP: Started")
    print("   ⏱️  Heartbeat: Every 30 seconds")
    print("   🔍 Checks: Tasks due in next 2 minutes\n")
    
    while worker_running:
        try:
            now = datetime.now(timezone.utc)
            prepare_threshold = now + timedelta(seconds=PREPARE_ADVANCE_TIME)
            
            # Find tasks that need preparation (2 minutes from now)
            tasks = await tasks_collection.find({
                "status": "pending",
                "due_date": {
                    "$gte": now,
                    "$lte": prepare_threshold
                }
            }).to_list(length=10)
            
            # Update heartbeat
            worker_metrics["last_prepare_check"] = datetime.now(timezone.utc)
            worker_metrics["prepare_loop_heartbeat"] += 1
            
            if tasks:
                print(f"\n🔍 Found {len(tasks)} task(s) to prepare")
                
                for task in tasks:
                    task_id = str(task['_id'])
                    
                    # Update to preparing status immediately
                    await tasks_collection.update_one(
                        {"_id": task['_id']},
                        {"$set": {"status": "preparing"}}
                    )
                    
                    # Prepare the email
                    success = await prepare_email(task)
                    
                    if success:
                        # Calculate exact send time
                        due_date = task.get('due_date')
                        # Make due_date timezone-aware if it's naive
                        if due_date and due_date.tzinfo is None:
                            due_date = due_date.replace(tzinfo=timezone.utc)
                        send_at = due_date.timestamp() if due_date else time.time()
                        
                        # Schedule for sending (sorted set by timestamp)
                        await redis_client.zadd(QUEUE_SEND, {task_id: send_at})
                        print(f"📅 Task {task_id} scheduled for {due_date}")
            
            # Sleep before next check
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            print(f"❌ Prepare loop error: {e}")
            await asyncio.sleep(30)


async def send_loop():
    """
    Background loop that sends prepared emails at exact scheduled time.
    Runs continuously, checking for tasks ready to send.
    print("   ⏱️  Heartbeat: Every 5 seconds")
    print("   ⚡ Checks: Tasks due right now\n")
    """
    print("\n📧 SEND LOOP: Started")
    
    while worker_running:
        try:
            now = time.time()
            
            # Get tasks that are due now (sorted by timestamp)
            due_tasks = await redis_client.zrangebyscore(
                QUEUE_SEND,
                '-inf',
                now,
                start=0,
                num=5  # Process 5 at a time
            )
            
            # Update heartbeat
            worker_metrics["last_send_check"] = datetime.now(timezone.utc)
            worker_metrics["send_loop_heartbeat"] += 1
            
            if due_tasks:
                print(f"\n⚡ Found {len(due_tasks)} email(s) ready to send")
                
                for task_id_bytes in due_tasks:
                    task_id = task_id_bytes.decode() if isinstance(task_id_bytes, bytes) else task_id_bytes
                    
                    # Remove from queue immediately
                    await redis_client.zrem(QUEUE_SEND, task_id)
                    
                    # Load task from database
                    task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
                    
                    if not task:
                        print(f"⚠️  Task {task_id} not found in database")
                        continue
                    
                    # Send the email
                    await send_prepared_email(task)
                    
                    # Handle recurring tasks
                    recurrence = task.get('recurrence')
                    if recurrence and task.get('status') == 'sent':
                        next_due = compute_next_due_date(task.get('due_date'), recurrence)
                        if next_due:
                            await tasks_collection.update_one(
                                {"_id": ObjectId(task_id)},
                                {"$set": {
                                    "status": "pending",
                                    "due_date": next_due,
                                    "updated_at": datetime.now(timezone.utc)
                                }}
                            )
                            print(f"♻️  Recurring task {task_id} rescheduled for {next_due}")
                        else:
                            # Mark as completed if no next occurrence
                            await tasks_collection.update_one(
                                {"_id": ObjectId(task_id)},
                                {"$set": {
                                    "status": "completed",
                                    "completed_at": datetime.now(timezone.utc)
                                }}
                            )
                    else:
                        # Mark one-time tasks as completed
                        if task.get('status') == 'sent':
                            await tasks_collection.update_one(
                                {"_id": ObjectId(task_id)},
                                {"$set": {
                                    "status": "completed",
                                    "completed_at": datetime.now(timezone.utc)
                                }}
                            )
            
            # Sleep before next check
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"❌ Send loop error: {e}")
            await asyncio.sleep(5)


def compute_next_due_date(current_due: datetime, recurrence: dict) -> Optional[datetime]:
    """Compute next occurrence for recurring tasks"""
    if not isinstance(current_due, datetime):
        return None
    
    rule_type = recurrence.get("type")
    
    if rule_type == "daily":
        return current_due + timedelta(days=1)
    elif rule_type == "weekday":
        next_dt = current_due + timedelta(days=1)
        while next_dt.weekday() >= 5:  # Skip weekends
            next_dt += timedelta(days=1)
        return next_dt
    elif rule_type == "interval_hours":
        hours = int(recurrence.get("interval_hours", 1))
        return current_due + timedelta(hours=hours)
    
    return None


# ============================================================================
# RECOVERY & BOOTSTRAP
# ============================================================================

async def bootstrap_worker():
    """
    Bootstrap worker on startup.
    Recovers any missed tasks from database.
    """
    print("\n🚀 WORKER BOOTSTRAP: Starting...")
    
    try:
        now = datetime.now(timezone.utc)
        
        # 1. Find tasks that should have been prepared but weren't
        missed_tasks = await tasks_collection.find({
            "status": "pending",
            "due_date": {
                "$gte": now,
                "$lte": now + timedelta(minutes=10)  # Next 10 minutes
            }
        }).to_list(length=100)
        
        if missed_tasks:
            print(f"🔄 Recovering {len(missed_tasks)} missed task(s)")
            for task in missed_tasks:
                task_id = str(task['_id'])
                due_date = task.get('due_date')
                
                # Make due_date timezone-aware if it's naive
                if due_date and due_date.tzinfo is None:
                    due_date = due_date.replace(tzinfo=timezone.utc)
                
                # If due within 2 minutes, prepare immediately
                if due_date <= now + timedelta(minutes=2):
                    await prepare_email(task)
                    send_at = due_date.timestamp()
                    await redis_client.zadd(QUEUE_SEND, {task_id: send_at})
                    print(f"✅ Recovered task {task_id}")
        
        # 2. Clear any stale locks (older than 5 minutes)
        # This is handled by Redis TTL automatically
        
        print("✅ Worker bootstrap complete")
        
    except Exception as e:
        print(f"❌ Bootstrap error: {e}")


# ============================================================================
# MAIN WORKER
# ============================================================================

async def metrics_loop():
    """
    Display metrics every 60 seconds for monitoring.
    """
    while worker_running:
        try:
            await asyncio.sleep(60)  # Every minute
            
            if not worker_running:
                break
            
            uptime = (datetime.now(timezone.utc) - worker_metrics["start_time"]).total_seconds()
            uptime_min = int(uptime / 60)
            
            print("\n" + "="*70)
            print("📊 WORKER METRICS - Status Report")
            print("="*70)
            print(f"⏱️  Uptime: {uptime_min} minutes")
            print(f"✅ Emails prepared: {worker_metrics['emails_prepared']}")
            print(f"📧 Emails sent: {worker_metrics['emails_sent']}")
            print(f"❌ Emails failed: {worker_metrics['emails_failed']}")
            print(f"🔄 Total retries: {worker_metrics['retries_total']}")
            print(f"💓 Prepare heartbeat: {worker_metrics['prepare_loop_heartbeat']}")
            print(f"💓 Send heartbeat: {worker_metrics['send_loop_heartbeat']}")
            
            # Check for stale heartbeats (alert)
            last_prepare = worker_metrics.get("last_prepare_check")
            last_send = worker_metrics.get("last_send_check")
            
            if last_prepare:
                prepare_age = (datetime.now(timezone.utc) - last_prepare).total_seconds()
                if prepare_age > 120:  # No check in 2 minutes
                    print(f"🚨 ALERT: Prepare loop stale ({prepare_age:.0f}s)")
            
            if last_send:
                send_age = (datetime.now(timezone.utc) - last_send).total_seconds()
                if send_age > 60:  # No check in 1 minute
                    print(f"🚨 ALERT: Send loop stale ({send_age:.0f}s)")
            
            print("="*70 + "\n")
            
        except Exception as e:
            print(f"⚠️  Metrics loop error: {e}")


async def start_worker():
    """
    Main worker entry point.
    Starts both prepare and send loops.
    """
    global worker_running
    worker_running = True
    worker_metrics["start_time"] = datetime.now(timezone.utc)
    
    print("\n" + "="*70)
    print("⚡ EMAIL WORKER - PRODUCTION MODE")
    print("="*70)
    print(f"📊 Configuration:")
    print(f"   Global rate limit: {GLOBAL_RATE_LIMIT}/min")
    print(f"   Per-user limit: {PER_USER_DAILY_LIMIT}/day")
    print(f"   Prepare advance: {PREPARE_ADVANCE_TIME}s")
    print(f"   SendGrid keys: {len([k for k in SENDGRID_KEYS if k])}")
    print("="*70 + "\n")
    
    # Bootstrap
    await bootstrap_worker()
    
    # Start all loops concurrently
    try:
        await asyncio.gather(
            prepare_loop(),
            send_loop(),
            metrics_loop()
        )
    except KeyboardInterrupt:
        print("\n⚠️  Worker shutting down...")
        worker_running = False
    except Exception as e:
        print(f"\n❌ Worker crashed: {e}")
        worker_running = False


if __name__ == "__main__":
    """Run worker as standalone process"""
    asyncio.run(start_worker())
