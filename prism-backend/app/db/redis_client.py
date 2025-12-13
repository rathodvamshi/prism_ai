# 💬 CHAT HISTORY OPERATIONS
async def get_recent_history(user_id: str, limit: int = 10) -> str:
    """Get recent chat history for a user from Redis."""
    key = f"CHAT_HISTORY:{user_id}"
    messages = await redis_client.lrange(key, -limit, -1)
    history = []
    for msg_json in messages:
        try:
            msg_data = json.loads(msg_json)
            history.append(f"[{msg_data['role']}]: {msg_data['content']}")
        except Exception:
            continue
    return "\n".join(history)

async def add_message_to_history(user_id: str, role: str, content: str):
    """Add a message to the user's chat history in Redis."""
    key = f"CHAT_HISTORY:{user_id}"
    message_data = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }
    await redis_client.rpush(key, json.dumps(message_data))
    await redis_client.ltrim(key, -100, -1)  # Keep last 100 messages
"""
⚡ REDIS CLOUD (Super Fast Cache)

Use Redis for things that expire:
- OTP for email updates
- Rate limits  
- Session tokens
- Temporary chat storage before saving to MongoDB

🟢 Rule: Redis keys always include userId to prevent mixing
"""

import redis.asyncio as redis
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)

# Create the connection pool with error handling
def create_redis_client():
    """Create Redis client with proper error handling"""
    try:
        if not settings.REDIS_URL or settings.REDIS_URL == "redis://localhost:6379/0":
            logger.warning("Using default local Redis configuration")
            return redis.Redis(
                host="localhost",
                port=6379,
                db=0,
                encoding="utf-8",
                decode_responses=True
            )
        else:
            return redis.from_url(
                settings.REDIS_URL, 
                encoding="utf-8", 
                decode_responses=True
            )
    except Exception as e:
        logger.error(f"Failed to create Redis client: {e}")
        logger.warning("Falling back to local Redis")
        return redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            encoding="utf-8",
            decode_responses=True
        )

class RedisClient:
    """Redis client wrapper with connection error handling"""
    
    def __init__(self):
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Redis client"""
        try:
            self._client = create_redis_client()
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            self._client = None
    
    async def ping(self) -> bool:
        """Test Redis connection"""
        try:
            if self._client:
                await self._client.ping()
                return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
        return False
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis with error handling"""
        try:
            if self._client:
                return await self._client.get(key)
        except Exception as e:
            logger.error(f"Redis GET failed for key {key}: {e}")
        return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis with error handling"""
        try:
            if self._client:
                await self._client.set(key, value, ex=ex)
                return True
        except Exception as e:
            logger.error(f"Redis SET failed for key {key}: {e}")
        return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis with error handling"""
        try:
            if self._client:
                await self._client.delete(key)
                return True
        except Exception as e:
            logger.error(f"Redis DELETE failed for key {key}: {e}")
        return False
    
    async def incr(self, key: str) -> Optional[int]:
        """Increment key in Redis with error handling"""
        try:
            if self._client:
                return await self._client.incr(key)
        except Exception as e:
            logger.error(f"Redis INCR failed for key {key}: {e}")
        return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key in Redis with error handling"""
        try:
            if self._client:
                await self._client.expire(key, seconds)
                return True
        except Exception as e:
            logger.error(f"Redis EXPIRE failed for key {key}: {e}")
        return False
    
    async def lrange(self, key: str, start: int, end: int) -> list:
        """Get list range from Redis with error handling"""
        try:
            if self._client:
                return await self._client.lrange(key, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE failed for key {key}: {e}")
        return []
    
    async def lpush(self, key: str, *values) -> bool:
        """Left push to Redis list with error handling"""
        try:
            if self._client:
                await self._client.lpush(key, *values)
                return True
        except Exception as e:
            logger.error(f"Redis LPUSH failed for key {key}: {e}")
        return False
    
    async def rpush(self, key: str, *values) -> bool:
        """Right push to Redis list with error handling"""
        try:
            if self._client:
                await self._client.rpush(key, *values)
                return True
        except Exception as e:
            logger.error(f"Redis RPUSH failed for key {key}: {e}")
        return False
    
    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim Redis list with error handling"""
        try:
            if self._client:
                await self._client.ltrim(key, start, end)
                return True
        except Exception as e:
            logger.error(f"Redis LTRIM failed for key {key}: {e}")
        return False
    
    async def keys(self, pattern: str) -> list:
        """Get keys matching pattern with error handling"""
        try:
            if self._client:
                return await self._client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS failed for pattern {pattern}: {e}")
        return []

# Global Redis client instance
redis_client = RedisClient()

# 🔐 OTP MANAGEMENT
async def store_otp(email: str, otp: str, expires_minutes: int = 2):
    """
    Store OTP for email verification.
    Redis key example: OTP:user@gmail.com = 573910 (expires in 2 minutes)
    """
    key = f"OTP:{email}"
    success = await redis_client.set(key, otp, ex=expires_minutes * 60)
    if success:
        logger.info(f"✅ OTP stored for {email}, expires in {expires_minutes} minutes")
    else:
        logger.error(f"❌ Failed to store OTP for {email}")

async def verify_otp(email: str, provided_otp: str) -> bool:
    """Verify OTP and delete it after verification"""
    key = f"OTP:{email}"
    stored_otp = await redis_client.get(key)
    
    if stored_otp and stored_otp == provided_otp:
        # Delete OTP after successful verification
        await redis_client.delete(key)
        logger.info(f"✅ OTP verified and deleted for {email}")
        return True
    return False

# 🛡️ RATE LIMITING
async def check_rate_limit(user_id: str, action: str, max_requests: int = 100, window_minutes: int = 60) -> bool:
    """
    Check if user is within rate limits.
    Redis key: RATE:{userId}:{action} = count
    """
    key = f"RATE:{user_id}:{action}"
    current_count = await redis_client.get(key)
    
    if current_count is None:
        # First request - set counter with expiry
        await redis_client.set(key, "1", ex=window_minutes * 60)
        return True
    
    if int(current_count) >= max_requests:
        return False  # Rate limit exceeded
    
    # Increment counter
    await redis_client.incr(key)
    return True

# 🎫 SESSION TOKEN MANAGEMENT  
async def store_session_token(user_id: str, token: str, expires_hours: int = 24):
    """Store session token for user"""
    key = f"SESSION:{user_id}"
    await redis_client.set(key, token, ex=expires_hours * 3600)

async def verify_session_token(user_id: str, token: str) -> bool:
    """Verify session token"""
    key = f"SESSION:{user_id}"
    stored_token = await redis_client.get(key)
    return stored_token == token if stored_token else False

async def revoke_session_token(user_id: str):
    """Revoke/delete session token"""
    key = f"SESSION:{user_id}"
    await redis_client.delete(key)

# 💬 TEMPORARY CHAT STORAGE (before saving to MongoDB)
async def cache_temp_message(user_id: str, session_id: str, role: str, content: str):
    """
    Temporarily cache message before saving to MongoDB.
    Key: TEMP_CHAT:{userId}:{sessionId}
    """
    key = f"TEMP_CHAT:{user_id}:{session_id}"
    message_data = {
        "role": role,
        "content": content, 
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add to list
    await redis_client.lpush(key, json.dumps(message_data))
    
    # Keep only last 50 messages in temp storage
    await redis_client.ltrim(key, 0, 49)
    
    # Expire after 1 hour (messages should be saved to MongoDB by then)
    await redis_client.expire(key, 3600)

async def get_temp_messages(user_id: str, session_id: str) -> list:
    """Get temporary messages for a session"""
    key = f"TEMP_CHAT:{user_id}:{session_id}"
    temp_messages = await redis_client.lrange(key, 0, -1)
    
    messages = []
    for msg_json in reversed(temp_messages):  # Reverse to get chronological order
        try:
            msg_data = json.loads(msg_json)
            messages.append(msg_data)
        except json.JSONDecodeError:
            continue
    
    return messages

async def clear_temp_messages(user_id: str, session_id: str):
    """Clear temporary messages after saving to MongoDB"""
    key = f"TEMP_CHAT:{user_id}:{session_id}"
    await redis_client.delete(key)

# 📊 USER ACTIVITY TRACKING
async def track_user_activity(user_id: str):
    """Track last activity time for user"""
    key = f"LAST_ACTIVE:{user_id}"
    await redis_client.set(key, datetime.utcnow().isoformat(), ex=86400)  # 24 hours

async def get_user_last_activity(user_id: str) -> Optional[datetime]:
    """Get user's last activity time"""
    key = f"LAST_ACTIVE:{user_id}"
    activity = await redis_client.get(key)
    
    if activity:
        try:
            return datetime.fromisoformat(activity)
        except ValueError:
            pass
    return None

# 🧹 UTILITY FUNCTIONS
async def clear_user_cache(user_id: str):
    """Clear all Redis entries for a user"""
    patterns = [
        f"RATE:{user_id}:*",
        f"SESSION:{user_id}",
        f"TEMP_CHAT:{user_id}:*", 
        f"LAST_ACTIVE:{user_id}"
    ]
    
    for pattern in patterns:
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
    
    print(f"✅ Cleared Redis cache for user: {user_id}")

async def get_redis_stats() -> Dict[str, Any]:
    """Get Redis usage statistics"""
    info = await redis_client.info()
    return {
        "total_keys": await redis_client.dbsize(),
        "memory_used": info.get("used_memory_human", "Unknown"),
        "connected_clients": info.get("connected_clients", 0)
    }

# 🚨 EMERGENCY FUNCTIONS
async def store_emergency_data(key: str, data: Dict[str, Any], expires_minutes: int = 30):
    """Store emergency data (like failed DB saves)"""
    emergency_key = f"EMERGENCY:{key}"
    await redis_client.set(emergency_key, json.dumps(data), ex=expires_minutes * 60)

async def get_emergency_data(key: str) -> Optional[Dict[str, Any]]:
    """Retrieve emergency data"""
    emergency_key = f"EMERGENCY:{key}"
    data = await redis_client.get(emergency_key)
    
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            pass
    return None

# 🧠 ADVANCED REDIS CLIENT FOR AI MEMORY MANAGEMENT

class AdvancedRedisClient:
    """Advanced Redis client with memory management for AI model integration"""
    
    def __init__(self):
        self.client = redis_client
    
    # TEMPORARY MEMORY OPERATIONS (Short-term mind)
    async def get_temp_memory(self, user_id: str) -> dict:
        """Get temporary memory for user"""
        try:
            key = f"TEMP_MEMORY:{user_id}"
            data = await self.client.get(key)
            return json.loads(data) if data else {}
        except Exception as e:
            print(f"Error getting temp memory: {e}")
            return {}
    
    async def set_temp_memory(self, user_id: str, memory: dict, expire_hours: int = 24) -> bool:
        """Set temporary memory for user (expires after specified hours)"""
        try:
            key = f"TEMP_MEMORY:{user_id}"
            await self.client.setex(key, expire_hours * 3600, json.dumps(memory))
            return True
        except Exception as e:
            print(f"Error setting temp memory: {e}")
            return False
    
    async def update_temp_memory(self, user_id: str, updates: dict) -> bool:
        """Update specific fields in temporary memory"""
        try:
            current = await self.get_temp_memory(user_id)
            current.update(updates)
            return await self.set_temp_memory(user_id, current)
        except Exception as e:
            print(f"Error updating temp memory: {e}")
            return False
    
    # SESSION STATE OPERATIONS
    async def get_session_state(self, user_id: str) -> dict:
        """Get current session state for user"""
        try:
            key = f"SESSION_STATE:{user_id}"
            data = await self.client.get(key)
            return json.loads(data) if data else {}
        except Exception as e:
            print(f"Error getting session state: {e}")
            return {}
    
    async def update_session_state(self, user_id: str, state: dict) -> bool:
        """Update session state for user"""
        try:
            key = f"SESSION_STATE:{user_id}"
            current = await self.get_session_state(user_id)
            current.update(state)
            current["lastUpdated"] = datetime.utcnow().isoformat()
            await self.client.setex(key, 86400, json.dumps(current))  # 24 hours
            return True
        except Exception as e:
            print(f"Error updating session state: {e}")
            return False
    
    # CONVERSATION CONTEXT OPERATIONS
    async def store_conversation_context(self, user_id: str, context: dict, expire_hours: int = 6) -> bool:
        """Store conversation context temporarily"""
        try:
            key = f"CONV_CONTEXT:{user_id}"
            await self.client.setex(key, expire_hours * 3600, json.dumps(context))
            return True
        except Exception as e:
            print(f"Error storing conversation context: {e}")
            return False
    
    async def get_conversation_context(self, user_id: str) -> dict:
        """Get conversation context for user"""
        try:
            key = f"CONV_CONTEXT:{user_id}"
            data = await self.client.get(key)
            return json.loads(data) if data else {}
        except Exception as e:
            print(f"Error getting conversation context: {e}")
            return {}
    
    # MEMORY PROCESSING FLAGS
    async def set_memory_processing_flag(self, user_id: str, flag_type: str, value: any, expire_minutes: int = 30) -> bool:
        """Set temporary processing flags for memory operations"""
        try:
            key = f"MEMORY_FLAG:{user_id}:{flag_type}"
            await self.client.setex(key, expire_minutes * 60, json.dumps(value))
            return True
        except Exception as e:
            print(f"Error setting memory flag: {e}")
            return False
    
    async def get_memory_processing_flag(self, user_id: str, flag_type: str) -> any:
        """Get memory processing flag"""
        try:
            key = f"MEMORY_FLAG:{user_id}:{flag_type}"
            data = await self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Error getting memory flag: {e}")
            return None
    
    # CLEANUP OPERATIONS
    async def clear_user_memories(self, user_id: str) -> bool:
        """Clear all memory-related Redis entries for a user"""
        try:
            patterns = [
                f"TEMP_MEMORY:{user_id}",
                f"SESSION_STATE:{user_id}",
                f"CONV_CONTEXT:{user_id}",
                f"MEMORY_FLAG:{user_id}:*"
            ]
            
            for pattern in patterns:
                if "*" in pattern:
                    keys = await self.client.keys(pattern)
                    if keys:
                        await self.client.delete(*keys)
                else:
                    await self.client.delete(pattern)
            
            return True
        except Exception as e:
            print(f"Error clearing user memories: {e}")
            return False