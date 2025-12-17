import json
from typing import Optional

from bson import ObjectId

from app.db.mongo_client import users_collection
from app.db.redis_client import redis_client


async def get_user_profile(user_id: str) -> Optional[dict]:
    """
    Fetch user profile with Redis caching (5 minute TTL).
    If not found or no timezone, caller can decide to ask the user once and then update profile.
    """
    cache_key = f"user:profile:{user_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    query_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    user = await users_collection.find_one({"_id": query_id})

    if user:
        try:
            await redis_client.set(cache_key, json.dumps(user, default=str), ex=300)
        except Exception:
            pass

    return user

