import asyncio
import json
from datetime import datetime, timezone, timedelta
import uuid

import pytest

from app.cognitive.temporal import resolve_time
from app.config import settings
from app.cognitive.context_stack import push_context, peek_context, pop_context, clear_context
from app.db.redis_client import redis_client, EMAIL_SCHEDULED_QUEUE
from app.services.email_queue_service import schedule_task_reminder, remove_scheduled_email


@pytest.mark.asyncio
async def test_relative_time_update_end_to_end():
    # Setup: unique user/session
    user_id = uuid.uuid4().hex
    session_id = uuid.uuid4().hex

    # 1) Create: "Remind me to Check Server Logs tomorrow at 9 AM."
    create_text = "Remind me to Check Server Logs tomorrow at 9 AM."
    # Compute tomorrow 9 AM in configured timezone (manual fallback)
    tzinfo = settings.tzinfo
    now_tz = datetime.now(tzinfo)
    tomorrow_tz = (now_tz + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    tr = resolve_time(create_text)  # try resolver too for parity
    # Store as task in simulated DB (in-memory)
    # Use a clean description that the update text can match reliably
    description = "Server Logs"
    # Convert ISO to naive UTC for storage
    # Prefer resolver result if available; fallback to manual
    if tr.target_time_iso:
        create_dt = datetime.fromisoformat(tr.target_time_iso.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    else:
        create_dt = tomorrow_tz.astimezone(timezone.utc).replace(tzinfo=None)
    tasks = {}
    task_id = uuid.uuid4().hex
    tasks[task_id] = {
        "userId": user_id,
        "description": description,
        "status": "pending",
        "due_date": create_dt,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    assert task_id in tasks, "Task was not created"

    # 2) Update (Ambiguous + Relative): "Actually, change Server Logs to 2 hours from now."
    update_text = "Actually, change Server Logs to 2 hours from now."
    # Ground relative time manually to avoid external parser variability
    base_now_tz = datetime.now(tzinfo)
    new_dt_tz = base_now_tz + timedelta(hours=2)
    new_time_iso = new_dt_tz.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    # Push pending_action into context, like streaming endpoint would
    await clear_context(user_id, session_id)
    await push_context(user_id, session_id, {"type": "pending_action", "intent": "task_update", "entities": {
        "task_id": task_id,
        "task_name": description,
        "new_time_iso": new_time_iso,
    }})

    # Confirm: "Yes" — retrieve ISO from Redis (no recalculation)
    pending = await peek_context(user_id, session_id)
    assert pending and pending.get("type") == "pending_action"
    iso_from_context = pending["entities"]["new_time_iso"]
    assert iso_from_context == new_time_iso, "ISO in context does not match router grounding"

    # Execute update using ISO from context
    new_dt = datetime.fromisoformat(iso_from_context.replace("Z", "+00:00"))
    new_dt_utc = new_dt.astimezone(timezone.utc)
    # Reject past times (guard)
    assert new_dt_utc > datetime.utcnow().replace(tzinfo=timezone.utc), "New time is in the past"

    naive_utc = new_dt_utc.replace(tzinfo=None)
    tasks[task_id]["due_date"] = naive_utc
    tasks[task_id]["updated_at"] = datetime.utcnow()

    # Reschedule email job (remove + add)
    await remove_scheduled_email(task_id)
    await schedule_task_reminder(task_id, user_id, new_dt_utc.timestamp())

    # Pop the context (confirmation complete)
    await pop_context(user_id, session_id)

    # Verify final scheduled time in Mongo
    stored_due = tasks[task_id].get("due_date")
    assert isinstance(stored_due, datetime)
    # Compare stored_due (naive UTC) to original grounded time
    stored_due_utc = stored_due.replace(tzinfo=timezone.utc)
    # Allow <= 1 second tolerance for conversion
    delta_seconds = abs((stored_due_utc - new_dt_utc).total_seconds())
    assert delta_seconds <= 1, f"Time drift detected in Mongo: {delta_seconds}s"

    # Verify scheduled email ZSet timestamp matches new_dt_utc.timestamp()
    zscore = await redis_client._client.zscore(EMAIL_SCHEDULED_QUEUE, task_id)
    assert zscore is not None, "Task not found in scheduled email ZSet"
    # zscore may be float, compare within tolerance
    assert abs(float(zscore) - float(new_dt_utc.timestamp())) <= 1, f"Time drift detected in Redis ZSet: {abs(float(zscore) - float(new_dt_utc.timestamp()))}s"

    # Final assertion: no drift
    print(json.dumps({
        "task_id": task_id,
        "new_time_iso": new_time_iso,
        "mongo_due_date_iso": stored_due_utc.isoformat().replace("+00:00", "Z"),
        "redis_zscore": zscore,
        "drift_seconds_mongo": delta_seconds,
        "drift_seconds_redis": abs(float(zscore) - float(new_dt_utc.timestamp())),
    }))
