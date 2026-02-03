import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging
from bson import ObjectId
from app.db.mongo_client import sessions_collection
from app.utils.timeout_utils import tracked_timeout, TimeoutConfig
from app.utils.preprocess import preprocess as safe_preprocess
from app.cognitive.router_engine import route_message
from app.db.redis_client import add_message_to_history

logger = logging.getLogger(__name__)

class ChatPipelineService:
    """
    Unifies chat message processing logic to avoid duplication.
    Handles persistence, intent routing, and context management.
    """

    async def persist_user_message(self, session_id: str, user_id: str, message: str) -> Dict[str, Any]:
        """
        Persists a user message to MongoDB and Redis history.
        Returns the created message object.
        """
        # Preprocess
        _pre = safe_preprocess(message)
        _raw_text = _pre["raw_text"]
        _working_text = _pre["working_text"]

        user_message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        user_message_doc = {
            "id": user_message_id,
            "role": "user",
            "content": _raw_text,
            "timestamp": timestamp,
        }

        # 1. MongoDB Update
        await tracked_timeout(
            sessions_collection.update_one(
                {
                    "$and": [
                        {"$or": [{"chat_id": session_id}, {"sessionId": session_id}]},
                        {"$or": [{"user_id": ObjectId(user_id)}, {"userId": ObjectId(user_id)}]}
                    ]
                },
                {
                    "$push": {"messages": user_message_doc},
                    "$set": {
                        "updated_at": timestamp,
                        "updatedAt": timestamp
                    }
                }
            ),
            timeout_ms=TimeoutConfig.MONGODB_UPDATE,
            service_name="MongoDB UPDATE (user message)",
            fallback=None
        )

        # 2. Redis History
        try:
             await add_message_to_history(str(user_id), "user", _raw_text)
        except Exception as e:
             logger.warning(f"⚠️ Failed to save user message to Redis history: {e}")

        return {
            "message_doc": user_message_doc,
            "raw_text": _raw_text,
            "working_text": _working_text
        }

    async def persist_ai_message(self, session_id: str, content: str, role: str = "assistant") -> Dict[str, Any]:
        """
        Persists an AI response to MongoDB.
        """
        ai_message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        ai_message_doc = {
            "id": ai_message_id,
            "role": role,
            "content": content,
            "timestamp": timestamp,
        }

        await tracked_timeout(
            sessions_collection.update_one(
                {
                    "$or": [{"chat_id": session_id}, {"sessionId": session_id}]
                },
                {
                    "$push": {"messages": ai_message_doc},
                    "$set": {
                        "updated_at": timestamp,
                        "updatedAt": timestamp
                    }
                }
            ),
            timeout_ms=TimeoutConfig.MONGODB_UPDATE,
            service_name="MongoDB UPDATE (AI message)",
            fallback=None
        )

        return ai_message_doc

chat_pipeline = ChatPipelineService()
