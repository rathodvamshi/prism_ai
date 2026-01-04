import uuid
import json
from datetime import datetime, timezone, timedelta

import pytest

from bson import ObjectId

from app.config import settings
from app.db.mongo_client import tasks_collection
from app.db.redis_client import redis_client, EMAIL_SCHEDULED_QUEUE
from app.services.email_queue_service import schedule_task_reminder, remove_scheduled_email


@pytest.mark.asyncio
async def test_live_relative_time_update_bson_and_ghost_job_check():
    """
    Live test against MongoDB and Redis to verify:
    - BSON round-trip: due_date stored as native Date (not string)
    - Ghost job: old scheduled reminder is removed; only new schedule remains
    """
    # Setup identifiers
    user_id = uuid.uuid4().hex
    description = "Server Logs"

    # 1) Create task with tomorrow at 9 AM (IST)
    tzinfo = settings.tzinfo
    now_tz = datetime.now(tzinfo)
    tomorrow_9_tz = (now_tz + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    tomorrow_9_utc = tomorrow_9_tz.astimezone(timezone.utc)
    # Enforce timezone-aware UTC write
    tomorrow_9_aware_utc = tomorrow_9_utc

    task_doc = {
        "userId": user_id,
        "description": description,
        "status": "pending",
        "due_date": tomorrow_9_aware_utc,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    insert_result = await tasks_collection.insert_one(task_doc)
    task_id = str(insert_result.inserted_id)

    # Schedule original reminder (simulate initial enqueue)
    await schedule_task_reminder(task_id, user_id, tomorrow_9_utc.timestamp())

    # Verify created and due_date is a Mongo Date (python datetime), not string
    created = await tasks_collection.find_one({"_id": insert_result.inserted_id, "userId": user_id})
    assert created is not None, "Task not found in Mongo"
    assert isinstance(created.get("due_date"), datetime), "due_date must be BSON Date (python datetime), not string"

    # 2) Update: new time is 2 hours from now
    new_dt_tz = datetime.now(tzinfo) + timedelta(hours=2)
    new_dt_utc = new_dt_tz.astimezone(timezone.utc)
    new_iso = new_dt_utc.isoformat().replace("+00:00", "Z")

    # Simulate confirmation YES using ISO from context (no recalculation)
    # Convert ISO to naive UTC for Mongo storage
    new_aware_utc = new_dt_utc
    await tasks_collection.update_one(
        {"_id": insert_result.inserted_id, "userId": user_id},
        {"$set": {"due_date": new_aware_utc, "updated_at": datetime.now(timezone.utc)}}
    )

    # Ghost Job Check: remove old schedule and add new
    await remove_scheduled_email(task_id)
    await schedule_task_reminder(task_id, user_id, new_dt_utc.timestamp())

    # Verify Mongo date is a Date and matches new time
    updated = await tasks_collection.find_one({"_id": insert_result.inserted_id, "userId": user_id})
    assert updated is not None
    stored_due = updated.get("due_date")
    assert isinstance(stored_due, datetime), "Updated due_date must be BSON Date"
    stored_due_utc = stored_due.replace(tzinfo=timezone.utc)
    assert abs((stored_due_utc - new_dt_utc).total_seconds()) <= 1, "Mongo due_date drift detected"

    # BSON Round-Trip Verification: range query should return the task
    day_start = new_dt_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    # Use naive UTC boundaries consistent with stored format
    day_start_naive = day_start.replace(tzinfo=None)
    day_end_naive = day_end.replace(tzinfo=None)
    in_range = await tasks_collection.find({
        "userId": user_id,
        "due_date": {"$gte": day_start_naive, "$lt": day_end_naive}
    }).to_list(length=10)
    assert any(t.get("_id") == insert_result.inserted_id for t in in_range), "Date range query failed; due_date may not be stored as Date"

    # Redis ZSet Verification
    zscore_new = await redis_client._client.zscore(EMAIL_SCHEDULED_QUEUE, task_id)
    assert zscore_new is not None, "Task not scheduled in Redis ZSet"
    # Ensure ZSet score equals new timestamp
    assert abs(float(zscore_new) - float(new_dt_utc.timestamp())) <= 1, "Redis scheduled time drift detected"
    # Ensure the old schedule is not present under the same member (overwrite or remove worked)
    # Since member is task_id, either zadd overwrote the score or zrem removed it; both acceptable.
    # We additionally assert the score does not equal the old timestamp.
    assert abs(float(zscore_new) - float(tomorrow_9_utc.timestamp())) > 1, "Ghost job detected: old schedule remains for same member"

    print(json.dumps({
        "task_id": task_id,
        "new_time_iso": new_iso,
        "mongo_due_date_iso": stored_due_utc.isoformat().replace("+00:00", "Z"),
        "redis_zscore": zscore_new,
    }))
