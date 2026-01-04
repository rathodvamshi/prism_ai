import uuid
from datetime import datetime, timezone, timedelta

import pytest

from bson import ObjectId

from app.main import app
from app.routers.chat import send_message_stream
from app.routers.chat import MessageRequest
from app.routers.auth import User
from app.db.mongo_client import sessions_collection, tasks_collection
from app.db.redis_client import redis_client, EMAIL_SCHEDULED_QUEUE


@pytest.mark.asyncio
async def test_streaming_task_update_end_to_end():
    """
    Black-box streaming test: User input -> Cognitive routing -> Confirmation -> DB update -> Redis reschedule -> User output.
    """
    # Setup user and session
    user_id = ObjectId()
    session_id = uuid.uuid4().hex
    chat_id = session_id

    # Create session
    await sessions_collection.insert_one({
        "userId": user_id,
        "sessionId": chat_id,
        "messages": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "isActive": True,
    })

    # Create an initial task (tomorrow at 9 AM IST)
    from app.config import settings
    tzinfo = settings.tzinfo
    now_tz = datetime.now(tzinfo)
    t9_tz = (now_tz + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    t9_utc = t9_tz.astimezone(timezone.utc)

    task = {
        "userId": str(user_id),
        "description": "Server Logs",
        "status": "pending",
        "due_date": t9_utc,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    ins = await tasks_collection.insert_one(task)
    task_id = str(ins.inserted_id)

    # Pre-populate context with pending_action like the router-confirmation step
    from app.cognitive.context_stack import push_context
    # Ground relative time ISO (2 hours from now) in UTC
    new_dt_utc = datetime.now(timezone.utc) + timedelta(hours=2)
    new_iso = new_dt_utc.isoformat().replace("+00:00", "Z")
    await push_context(str(user_id), chat_id, {
        "type": "pending_action",
        "intent": "task_update",
        "entities": {"task_id": task_id, "task_name": "Server Logs", "new_time_iso": new_iso}
    })

    # Streaming call: user confirms "Yes"
    user = User(user_id=str(user_id), email="test@example.com", name="Test User")
    req2 = MessageRequest(chatId=chat_id, message="Yes")
    stream2 = await send_message_stream(req2, user)
    done_received = False
    async for chunk in stream2.body_iterator:
        data = chunk.decode("utf-8") if isinstance(chunk, (bytes, bytearray)) else str(chunk)
        if data.startswith("event: done"):
            done_received = True
            break
    assert done_received, "Streaming did not emit done after confirmation"

    # Verify task updated and rescheduled
    updated = await tasks_collection.find_one({"_id": ins.inserted_id, "userId": str(user_id)})
    assert updated is not None
    new_due = updated.get("due_date")
    assert isinstance(new_due, datetime), "due_date must be a datetime"
    # Verify Redis ZSet reflects the new time
    zscore = await redis_client._client.zscore(EMAIL_SCHEDULED_QUEUE, task_id)
    assert zscore is not None, "Task not scheduled after update"
    # Timestamp compare tolerance
    assert abs(float(zscore) - float(new_due.replace(tzinfo=timezone.utc).timestamp())) <= 2, "Redis schedule mismatch with Mongo due_date"
