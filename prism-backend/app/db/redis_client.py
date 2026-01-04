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

# --------------------------------------------------
# Email Queue Key Definitions (Dual-Lane Architecture)
# --------------------------------------------------
EMAIL_HIGH_PRIORITY_QUEUE = "queue:email:high_priority"  # OTP/Auth lane (List)
EMAIL_SCHEDULED_QUEUE = "queue:email:scheduled"  # Task reminders lane (Sorted Set)
EMAIL_DAILY_LIMIT_KEY_TEMPLATE = "limit:email:{user_id}:{date}"  # Per-user/day counter
EMAIL_LOCK_KEY_TEMPLATE = "lock:email:{task_id}"  # Idempotency lock per task
EMAIL_DLQ = "queue:email:dlq"  # Dead-letter queue for failed sends

logger = logging.getLogger(__name__)

# Create the connection pool with error handling
def create_redis_client():
    """
    Create Redis client with connection pooling.
    
    ⚡ CONNECTION POOLING:
    - max_connections=50: Reuse up to 50 connections
    - socket_keepalive=True: Keep connections alive
    - retry_on_timeout=True: Auto-retry on timeout
    
    ❌ NEVER create Redis clients per request - use singleton!
    """
    try:
        if not settings.REDIS_URL or settings.REDIS_URL == "redis://localhost:6379/0":
            logger.warning("Using default local Redis configuration")
            # Create connection pool for local Redis
            pool = redis.ConnectionPool(
                host="localhost",
                port=6379,
                db=0,
                max_connections=50,
                socket_timeout=5,
                socket_connect_timeout=5,
                socket_keepalive=True,
                retry_on_timeout=True,
                encoding="utf-8",
                decode_responses=True
            )
            return redis.Redis(connection_pool=pool)
        else:
            # Create connection pool from URL
            return redis.from_url(
                settings.REDIS_URL,
                max_connections=50,
                socket_timeout=5,
                socket_connect_timeout=5,
                socket_keepalive=True,
                retry_on_timeout=True,
                encoding="utf-8",
                decode_responses=True
            )
    except Exception as e:
        logger.error(f"Failed to create Redis client: {e}")
        logger.warning("Falling back to local Redis with connection pool")
        pool = redis.ConnectionPool(
            host="localhost",
            port=6379,
            db=0,
            max_connections=50,
            encoding="utf-8",
            decode_responses=True
        )
        return redis.Redis(connection_pool=pool)

class RedisClient:
    """
    🔌 SINGLETON Redis client with connection pooling.
    
    ✅ MANDATORY PATTERNS:
    - Only ONE instance exists (singleton)
    - Reuses connections from pool
    - Never creates clients per request
    
    ❌ NEVER DO THIS:
    ```python
    # BAD - Creates new client per request ❌
    client = RedisClient()
    ```
    
    ✅ ALWAYS DO THIS:
    ```python
    # GOOD - Use global singleton ✅
    from app.db.redis_client import redis_client
    await redis_client.get(key)
    ```
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Enforce singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis client only once"""
        if not self._initialized:
            self._client = None
            self._initialize_client()
            RedisClient._initialized = True
    
    def _initialize_client(self):
        """Initialize Redis client with connection pool"""
        try:
            self._client = create_redis_client()
            logger.info("✅ Redis singleton client initialized with connection pool")
            logger.info("   Max connections: 50 (pooled)")
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
    
    async def set(self, key: str, value: str, ex: Optional[int] = None, nx: bool = False) -> bool:
        """Set value in Redis with error handling"""
        try:
            if self._client:
                result = await self._client.set(key, value, ex=ex, nx=nx)
                # When nx=True, returns True if key was set, None if key already exists
                return result if nx else True
        except Exception as e:
            logger.error(f"Redis SET failed for key {key}: {e}")
        return False
    
    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """
        Set value with TTL (seconds) in Redis with error handling.
        This mirrors the low-level setex, but uses SET with ex= for compatibility.
        """
        try:
            if self._client:
                await self._client.set(key, value, ex=seconds)
                return True
        except Exception as e:
            logger.error(f"Redis SETEX failed for key {key}: {e}")
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
    
    async def lpop(self, key: str) -> Optional[str]:
        """Left pop from Redis list with error handling"""
        try:
            if self._client:
                return await self._client.lpop(key)
        except Exception as e:
            logger.error(f"Redis LPOP failed for key {key}: {e}")
        return None
    
    async def rpop(self, key: str) -> Optional[str]:
        """Right pop from Redis list with error handling"""
        try:
            if self._client:
                return await self._client.rpop(key)
        except Exception as e:
            logger.error(f"Redis RPOP failed for key {key}: {e}")
        return None
    
    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim Redis list with error handling"""
        try:
            if self._client:
                await self._client.ltrim(key, start, end)
                return True
        except Exception as e:
            logger.error(f"Redis LTRIM failed for key {key}: {e}")
        return False
    
    async def zadd(self, key: str, mapping: dict, **kwargs) -> bool:
        """Add to sorted set with error handling"""
        try:
            if self._client:
                await self._client.zadd(key, mapping, **kwargs)
                return True
        except Exception as e:
            logger.error(f"Redis ZADD failed for key {key}: {e}")
        return False
    
    async def zrangebyscore(self, key: str, min_score: str, max_score: str, start: int = 0, num: int = -1) -> list:
        """Get sorted set members by score range with error handling"""
        try:
            if self._client:
                return await self._client.zrangebyscore(key, min_score, max_score, start=start, num=num)
        except Exception as e:
            logger.error(f"Redis ZRANGEBYSCORE failed for key {key}: {e}")
        return []
    
    async def zrem(self, key: str, *members) -> bool:
        """Remove from sorted set with error handling"""
        try:
            if self._client:
                await self._client.zrem(key, *members)
                return True
        except Exception as e:
            logger.error(f"Redis ZREM failed for key {key}: {e}")
        return False
    
    async def zcard(self, key: str) -> int:
        """Get sorted set size with error handling"""
        try:
            if self._client:
                return await self._client.zcard(key)
        except Exception as e:
            logger.error(f"Redis ZCARD failed for key {key}: {e}")
        return 0
    
    async def keys(self, pattern: str) -> list:
        """Get keys matching pattern with error handling"""
        try:
            if self._client:
                return await self._client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS failed for pattern {pattern}: {e}")
        return []
    
    async def info(self) -> Dict[str, Any]:
        """Get Redis INFO with error handling"""
        try:
            if self._client:
                return await self._client.info()
        except Exception as e:
            logger.error(f"Redis INFO failed: {e}")
        return {}
    
    async def dbsize(self) -> int:
        """Get Redis DB size with error handling"""
        try:
            if self._client:
                return await self._client.dbsize()
        except Exception as e:
            logger.error(f"Redis DBSIZE failed: {e}")
        return 0

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

# 📜 CHAT HISTORY MANAGEMENT
async def add_message_to_history(user_id: str, role: str, content: str):
    """
    Add message to user's chat history in Redis.
    Key: CHAT_HISTORY:{userId}
    """
    try:
        key = f"CHAT_HISTORY:{user_id}"
        message_data = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Push to list
        await redis_client.rpush(key, json.dumps(message_data))
        
        # Keep last 100 messages (Extended from 50)
        await redis_client.ltrim(key, -100, -1)
        
        # Set expiry (30 days - User requested long memory)
        await redis_client.expire(key, 2592000)
        
    except Exception as e:
        logger.error(f"Failed to add message to history: {e}")

async def get_recent_history(user_id: str, limit: int = 10) -> str:
    """
    Get recent chat history formatted for LLM context.
    Returns string:
    User: hello
    Assistant: hi
    """
    try:
        key = f"CHAT_HISTORY:{user_id}"
        # Get last N messages
        messages = await redis_client.lrange(key, -limit, -1)
        
        formatted_history = []
        for msg_json in messages:
            try:
                msg = json.loads(msg_json)
                role = msg.get("role", "unknown").capitalize()
                content = msg.get("content", "")
                
                # Normalize roles
                if role.lower() in ["user", "human"]:
                    role = "User"
                elif role.lower() in ["assistant", "ai", "system"]:
                    role = "Assistant"
                    
                formatted_history.append(f"{role}: {content}")
            except json.JSONDecodeError:
                continue
                
        return "\n\n".join(formatted_history)
        
    except Exception as e:
        logger.error(f"Failed to get recent history: {e}")
        return ""

# 🧠 MINI-AGENT CONVERSATION MEMORY (MESSAGE-SCOPED)
async def store_mini_agent_context(user_id: str, message_id: str, question: str, answer: str, ttl_minutes: int = 30):
    """
    Store mini-agent clarification for a specific message.
    Key: MINI_AGENT:{user_id}:{message_id}
    TTL: 30 minutes (conversation flow expires after inactivity)
    """
    try:
        key = f"MINI_AGENT:{user_id}:{message_id}"
        
        # Get existing context or create new
        existing_data = await redis_client.get(key)
        if existing_data:
            context = json.loads(existing_data)
        else:
            context = {
                "message_id": message_id,
                "clarifications": [],
                "created_at": datetime.utcnow().isoformat()
            }
        
        # Add new clarification
        context["clarifications"].append({
            "question": question,
            "answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 5 clarifications
        context["clarifications"] = context["clarifications"][-5:]
        context["last_updated"] = datetime.utcnow().isoformat()
        
        # Store with TTL
        await redis_client.setex(key, ttl_minutes * 60, json.dumps(context))
        
        logger.info(f"✅ Stored mini-agent context for message {message_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store mini-agent context: {e}")
        return False

async def get_mini_agent_context(user_id: str, message_id: str) -> dict:
    """
    Get mini-agent conversation history for a specific message.
    Returns: {"clarifications": [{"question": "...", "answer": "..."}], ...}
    """
    try:
        key = f"MINI_AGENT:{user_id}:{message_id}"
        data = await redis_client.get(key)
        
        if data:
            context = json.loads(data)
            logger.info(f"✅ Retrieved mini-agent context for message {message_id} ({len(context.get('clarifications', []))} clarifications)")
            return context
        
        return {"clarifications": []}
        
    except Exception as e:
        logger.error(f"Failed to get mini-agent context: {e}")
        return {"clarifications": []}

async def format_mini_agent_history(user_id: str, message_id: str) -> str:
    """
    Format mini-agent conversation history for LLM context.
    Returns formatted string of previous Q&A pairs.
    """
    try:
        context = await get_mini_agent_context(user_id, message_id)
        clarifications = context.get("clarifications", [])
        
        if not clarifications:
            return ""
        
        # Format as conversation
        formatted = []
        for clarification in clarifications:
            q = clarification.get("question", "")
            a = clarification.get("answer", "")
            formatted.append(f"User: {q}\nAssistant: {a}")
        
        return "\n\n".join(formatted)
        
    except Exception as e:
        logger.error(f"Failed to format mini-agent history: {e}")
        return ""

async def clear_mini_agent_context(user_id: str, message_id: str):
    """Clear mini-agent conversation for a specific message"""
    try:
        key = f"MINI_AGENT:{user_id}:{message_id}"
        await redis_client.delete(key)
        logger.info(f"✅ Cleared mini-agent context for message {message_id}")
    except Exception as e:
        logger.error(f"Failed to clear mini-agent context: {e}")
