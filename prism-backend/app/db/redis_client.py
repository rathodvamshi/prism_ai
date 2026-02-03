"""
⚡ REDIS CLOUD (Super Fast Cache)

Use Redis for things that expire:
- OTP for email updates
- Rate limits  
- Session tokens
- Temporary chat storage before saving to MongoDB

🟢 Rule: Redis keys always include userId to prevent mixing

⚠️ IN-MEMORY FALLBACK: When Redis is unavailable, uses in-memory store
   - Works for local development without Redis
   - NOT recommended for production (no persistence, no TTL cleanup)
"""

import redis.asyncio as redis
import json
import logging
import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.config import settings

# Initialize logger early for use in InMemoryStore
logger = logging.getLogger(__name__)


# =============================================================================
# 🧠 IN-MEMORY FALLBACK STORE (Used when Redis is unavailable)
# =============================================================================
class InMemoryStore:
    """
    Simple in-memory key-value store with TTL support.
    Used as fallback when Redis connection fails.
    ⚠️ WARNING: Not suitable for production - no persistence, no clustering!
    """
    
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}  # key -> expiry timestamp
        self._lists: Dict[str, list] = {}
        self._sorted_sets: Dict[str, Dict[str, float]] = {}
        self._lock = asyncio.Lock()
        logger.info("🧠 InMemoryStore initialized (Redis fallback mode)")
    
    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired"""
        if key in self._expiry:
            if time.time() > self._expiry[key]:
                # Clean up expired key
                self._store.pop(key, None)
                self._expiry.pop(key, None)
                return True
        return False
    
    async def ping(self) -> bool:
        """Always returns True for in-memory store"""
        return True
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        async with self._lock:
            if self._is_expired(key):
                return False
            return key in self._store or key in self._lists or key in self._sorted_sets
    
    async def get(self, key: str) -> Optional[str]:
        """Get value"""
        async with self._lock:
            if self._is_expired(key):
                return None
            return self._store.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None, nx: bool = False) -> bool:
        """Set value with optional TTL"""
        async with self._lock:
            if nx and key in self._store and not self._is_expired(key):
                return False  # Key exists and nx=True
            self._store[key] = value
            if ex:
                self._expiry[key] = time.time() + ex
            return True
    
    async def append(self, key: str, value: str) -> bool:
        """Append to value"""
        async with self._lock:
            if self._is_expired(key):
                self._store[key] = value
            else:
                self._store[key] = self._store.get(key, "") + value
            return True
    
    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set with expiry"""
        return await self.set(key, value, ex=seconds)
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        async with self._lock:
            self._store.pop(key, None)
            self._expiry.pop(key, None)
            self._lists.pop(key, None)
            self._sorted_sets.pop(key, None)
            return True
    
    async def incr(self, key: str) -> int:
        """Increment value"""
        async with self._lock:
            if self._is_expired(key):
                self._store[key] = "0"
            current = int(self._store.get(key, "0"))
            current += 1
            self._store[key] = str(current)
            return current
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set TTL on key"""
        async with self._lock:
            if key in self._store or key in self._lists or key in self._sorted_sets:
                self._expiry[key] = time.time() + seconds
                return True
            return False
    
    async def lrange(self, key: str, start: int, end: int) -> list:
        """Get list range"""
        async with self._lock:
            lst = self._lists.get(key, [])
            if end == -1:
                return lst[start:]
            return lst[start:end+1]
    
    async def lpush(self, key: str, *values) -> bool:
        """Left push to list"""
        async with self._lock:
            if key not in self._lists:
                self._lists[key] = []
            for v in reversed(values):
                self._lists[key].insert(0, v)
            return True
    
    async def rpush(self, key: str, *values) -> bool:
        """Right push to list"""
        async with self._lock:
            if key not in self._lists:
                self._lists[key] = []
            self._lists[key].extend(values)
            return True
    
    async def lpop(self, key: str) -> Optional[str]:
        """Left pop from list"""
        async with self._lock:
            lst = self._lists.get(key, [])
            if lst:
                return lst.pop(0)
            return None
    
    async def rpop(self, key: str) -> Optional[str]:
        """Right pop from list"""
        async with self._lock:
            lst = self._lists.get(key, [])
            if lst:
                return lst.pop()
            return None
    
    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim list"""
        async with self._lock:
            if key in self._lists:
                if end == -1:
                    self._lists[key] = self._lists[key][start:]
                else:
                    self._lists[key] = self._lists[key][start:end+1]
            return True
    
    async def zadd(self, key: str, mapping: dict, **kwargs) -> bool:
        """Add to sorted set"""
        async with self._lock:
            if key not in self._sorted_sets:
                self._sorted_sets[key] = {}
            self._sorted_sets[key].update(mapping)
            return True
    
    async def zrangebyscore(self, key: str, min_score: str, max_score: str, start: int = 0, num: int = -1) -> list:
        """Get sorted set members by score"""
        async with self._lock:
            ss = self._sorted_sets.get(key, {})
            min_s = float('-inf') if min_score == '-inf' else float(min_score)
            max_s = float('inf') if max_score == '+inf' else float(max_score)
            items = [(k, v) for k, v in ss.items() if min_s <= v <= max_s]
            items.sort(key=lambda x: x[1])
            members = [k for k, v in items]
            if num == -1:
                return members[start:]
            return members[start:start+num]
    
    async def zrem(self, key: str, *members) -> bool:
        """Remove from sorted set"""
        async with self._lock:
            if key in self._sorted_sets:
                for m in members:
                    self._sorted_sets[key].pop(m, None)
            return True
    
    async def zcard(self, key: str) -> int:
        """Get sorted set size"""
        async with self._lock:
            return len(self._sorted_sets.get(key, {}))
    
    async def keys(self, pattern: str) -> list:
        """Get keys matching pattern (simple wildcard support)"""
        async with self._lock:
            import fnmatch
            all_keys = list(self._store.keys()) + list(self._lists.keys()) + list(self._sorted_sets.keys())
            return [k for k in all_keys if fnmatch.fnmatch(k, pattern)]
    
    async def info(self) -> Dict[str, Any]:
        """Get store info"""
        return {
            "mode": "in-memory-fallback",
            "keys": len(self._store) + len(self._lists) + len(self._sorted_sets),
            "warning": "Using in-memory fallback - no persistence!"
        }
    
    async def dbsize(self) -> int:
        """Get total key count"""
        return len(self._store) + len(self._lists) + len(self._sorted_sets)
    
    def register_script(self, script: str):
        """
        Register a Lua script for InMemoryStore fallback.
        Returns a callable that simulates script execution.
        ⚠️ Simplified fallback - supports GenerationManager CREATE_GENERATION_LUA pattern.
        """
        async def execute_script(keys: list = None, args: list = None):
            """
            Atomic Lua script simulator for InMemoryStore.
            Handles CREATE_GENERATION_LUA pattern with proper locking.
            """
            keys = keys or []
            args = args or []
            
            try:
                # Validate minimum required keys/args
                if len(keys) < 4 or len(args) < 5:
                    logger.warning(f"Script called with insufficient params: keys={len(keys)}, args={len(args)}")
                    return ['ERROR', '', 'Insufficient parameters']
                
                # Parse keys
                cooldown_key = keys[0]
                active_key = keys[1]
                lock_key = keys[2]
                gen_key = keys[3]
                
                # Parse args with type safety
                lock_timeout = int(args[0]) if args[0] else 1
                cooldown_ttl = int(args[1]) if args[1] else 1
                state_ttl = int(args[2]) if args[2] else 3600
                gen_id = str(args[3]) if args[3] else ""
                state_json = str(args[4]) if args[4] else "{}"
                
                # ATOMIC BLOCK START (simulated via Python lock)
                async with self._lock:
                    # Step 1: Check cooldown (fast fail)
                    if await self.exists(cooldown_key):
                        return ['COOLDOWN', '', '']
                    
                    # Step 2: Try to acquire lock
                    lock_acquired = await self.set(lock_key, 'locked', ex=lock_timeout, nx=True)
                    if not lock_acquired:
                        existing_gen_id = await self.get(active_key) or ''
                        existing_state = ''
                        if existing_gen_id:
                            existing_state = await self.get(f'generation:{existing_gen_id}') or ''
                        return ['LOCKED', existing_gen_id, existing_state]
                    
                    # Step 3: Set cooldown
                    await self.setex(cooldown_key, cooldown_ttl, '1')
                    
                    # Step 4: Get existing active generation
                    existing_gen_id = await self.get(active_key) or ''
                    existing_state_json = ''
                    if existing_gen_id:
                        existing_state_json = await self.get(f'generation:{existing_gen_id}') or ''
                    
                    # Step 5: Create new generation atomically
                    await self.setex(gen_key, state_ttl, state_json)
                    await self.setex(active_key, state_ttl, gen_id)
                    await self.delete(lock_key)  # Release lock
                # ATOMIC BLOCK END
                
                return ['OK', existing_gen_id, existing_state_json]
                
            except Exception as e:
                logger.error(f"InMemoryStore script error: {type(e).__name__}: {e}")
                # Attempt lock cleanup on error
                try:
                    if len(keys) > 2:
                        await self.delete(keys[2])  # Release lock_key
                except:
                    pass
                return ['ERROR', '', str(e)]
        
        return execute_script
    
    async def hset(self, name: str, key: str = None, value: str = None, mapping: dict = None) -> int:
        """Set hash field(s)"""
        async with self._lock:
            if name not in self._store:
                self._store[name] = {}
            if mapping:
                self._store[name].update(mapping)
                return len(mapping)
            elif key is not None:
                self._store[name][key] = value
                return 1
            return 0
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field"""
        async with self._lock:
            return self._store.get(name, {}).get(key)
    
    async def hgetall(self, name: str) -> dict:
        """Get all hash fields"""
        async with self._lock:
            return dict(self._store.get(name, {}))

# --------------------------------------------------
# Email Queue Key Definitions (Dual-Lane Architecture)
# --------------------------------------------------
EMAIL_HIGH_PRIORITY_QUEUE = "queue:email:high_priority"  # OTP/Auth lane (List)
EMAIL_SCHEDULED_QUEUE = "queue:email:scheduled"  # Task reminders lane (Sorted Set)
EMAIL_DAILY_LIMIT_KEY_TEMPLATE = "limit:email:{user_id}:{date}"  # Per-user/day counter
EMAIL_LOCK_KEY_TEMPLATE = "lock:email:{task_id}"  # Idempotency lock per task
EMAIL_DLQ = "queue:email:dlq"  # Dead-letter queue for failed sends

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
    - ⚠️ Falls back to in-memory store if Redis unavailable
    
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
            self._fallback = None  # In-memory fallback
            self._use_fallback = False
            self._initialize_client()
            RedisClient._initialized = True
    
    def _initialize_client(self):
        """Initialize Redis client with connection pool, fallback to in-memory if fails"""
        try:
            self._client = create_redis_client()
            logger.info("✅ Redis singleton client initialized with connection pool")
            logger.info("   Max connections: 50 (pooled)")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            self._client = None
            self._enable_fallback()
    
    def _enable_fallback(self):
        """Enable in-memory fallback mode"""
        if not self._fallback:
            self._fallback = InMemoryStore()
        self._use_fallback = True
        if settings.ENVIRONMENT != "development":
             logger.warning("⚠️ Redis unavailable - using in-memory fallback (NOT for production!)")
        else:
             logger.info("ℹ️ Redis unavailable - using in-memory fallback (Development Mode)")
    
    async def _check_connection(self) -> bool:
        """Check if Redis is connected, enable fallback if not"""
        if self._use_fallback:
            return True  # Fallback is always "connected"
        
        if not self._client:
            self._enable_fallback()
            return True
        
        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection check failed: {e}")
            self._enable_fallback()
            return True
    
    def _get_store(self):
        """Get the active store (Redis or fallback)"""
        if self._use_fallback:
            return self._fallback
        return self._client
    
    async def ping(self) -> bool:
        """Test Redis connection (or fallback)"""
        if self._use_fallback:
            return await self._fallback.ping()
        try:
            if self._client:
                await self._client.ping()
                return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            self._enable_fallback()
            return await self._fallback.ping()
        return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.exists(key)
            return await store.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.exists(key)
    
    async def get(self, key: str) -> Optional[str]:
        """Get value with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            return await store.get(key)
        except Exception as e:
            logger.error(f"Redis GET failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None, nx: bool = False) -> bool:
        """Set value with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.set(key, value, ex=ex, nx=nx)
            result = await store.set(key, value, ex=ex, nx=nx)
            return result if nx else True
        except Exception as e:
            logger.error(f"Redis SET failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.set(key, value, ex=ex, nx=nx)

    async def append(self, key: str, value: str) -> bool:
        """Append value with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.append(key, value)
            await store.append(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis APPEND failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.append(key, value)
    
    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set value with TTL with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.setex(key, seconds, value)
            await store.set(key, value, ex=seconds)
            return True
        except Exception as e:
            logger.error(f"Redis SETEX failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.setex(key, seconds, value)
    
    async def delete(self, key: str) -> bool:
        """Delete key with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.delete(key)
            await store.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.delete(key)
    
    async def incr(self, key: str) -> Optional[int]:
        """Increment key with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            return await store.incr(key)
        except Exception as e:
            logger.error(f"Redis INCR failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.incr(key)
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.expire(key, seconds)
            await store.expire(key, seconds)
            return True
        except Exception as e:
            logger.error(f"Redis EXPIRE failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.expire(key, seconds)
    
    async def lrange(self, key: str, start: int, end: int) -> list:
        """Get list range with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            return await store.lrange(key, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.lrange(key, start, end)
    
    async def lpush(self, key: str, *values) -> bool:
        """Left push with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.lpush(key, *values)
            await store.lpush(key, *values)
            return True
        except Exception as e:
            logger.error(f"Redis LPUSH failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.lpush(key, *values)
    
    async def rpush(self, key: str, *values) -> bool:
        """Right push with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.rpush(key, *values)
            await store.rpush(key, *values)
            return True
        except Exception as e:
            logger.error(f"Redis RPUSH failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.rpush(key, *values)
    
    async def lpop(self, key: str) -> Optional[str]:
        """Left pop with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            return await store.lpop(key)
        except Exception as e:
            logger.error(f"Redis LPOP failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.lpop(key)
    
    async def rpop(self, key: str) -> Optional[str]:
        """Right pop with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            return await store.rpop(key)
        except Exception as e:
            logger.error(f"Redis RPOP failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.rpop(key)
    
    async def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim list with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.ltrim(key, start, end)
            await store.ltrim(key, start, end)
            return True
        except Exception as e:
            logger.error(f"Redis LTRIM failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.ltrim(key, start, end)
    
    async def zadd(self, key: str, mapping: dict, **kwargs) -> bool:
        """Add to sorted set with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.zadd(key, mapping, **kwargs)
            await store.zadd(key, mapping, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Redis ZADD failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.zadd(key, mapping, **kwargs)
    
    async def zrangebyscore(self, key: str, min_score: str, max_score: str, start: int = 0, num: int = -1) -> list:
        """Get sorted set members by score with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.zrangebyscore(key, min_score, max_score, start=start, num=num)
            return await store.zrangebyscore(key, min_score, max_score, start=start, num=num)
        except Exception as e:
            logger.error(f"Redis ZRANGEBYSCORE failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.zrangebyscore(key, min_score, max_score, start=start, num=num)
    
    async def zrem(self, key: str, *members) -> bool:
        """Remove from sorted set with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.zrem(key, *members)
            await store.zrem(key, *members)
            return True
        except Exception as e:
            logger.error(f"Redis ZREM failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.zrem(key, *members)
    
    async def zcard(self, key: str) -> int:
        """Get sorted set size with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            return await store.zcard(key)
        except Exception as e:
            logger.error(f"Redis ZCARD failed for key {key}: {e}")
            self._enable_fallback()
            return await self._fallback.zcard(key)
    
    async def keys(self, pattern: str) -> list:
        """Get keys matching pattern with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            return await store.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS failed for pattern {pattern}: {e}")
            self._enable_fallback()
            return await self._fallback.keys(pattern)
    
    async def info(self) -> Dict[str, Any]:
        """Get info with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            return await store.info()
        except Exception as e:
            logger.error(f"Redis INFO failed: {e}")
            self._enable_fallback()
            return await self._fallback.info()
    
    async def dbsize(self) -> int:
        """Get DB size with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            return await store.dbsize()
        except Exception as e:
            logger.error(f"Redis DBSIZE failed: {e}")
            self._enable_fallback()
            return await self._fallback.dbsize()
    
    def is_using_fallback(self) -> bool:
        """Check if using in-memory fallback"""
        return self._use_fallback
    
    def register_script(self, script: str):
        """
        Register a Lua script for atomic Redis operations.
        
        🚀 LUA SCRIPTS:
        - Execute multiple Redis commands atomically on the server
        - Used by GenerationManager for race-condition-free generation creation
        - Falls back to InMemoryStore simulation if Redis unavailable
        
        Returns a callable that can execute the script with keys and args.
        """
        # Check fallback status
        if self._use_fallback:
            return self._fallback.register_script(script)
        
        if not self._client:
            self._enable_fallback()
            return self._fallback.register_script(script)
        
        # Register script with real Redis client
        try:
            redis_script = self._client.register_script(script)
        except Exception as e:
            logger.error(f"Failed to register Redis script: {e}")
            self._enable_fallback()
            return self._fallback.register_script(script)
        
        # Wrapper with connection recovery
        async def execute_script(keys: list = None, args: list = None):
            """Execute the registered Lua script with error recovery"""
            keys = keys or []
            args = args or []
            
            try:
                result = await redis_script(keys=keys, args=args)
                return result
            except Exception as e:
                error_str = str(e).lower()
                
                # Connection errors - switch to fallback for this execution
                if any(x in error_str for x in ['connection', 'timeout', 'refused', 'reset']):
                    logger.warning(f"Redis connection error during script: {e}")
                    # Execute via fallback for this call only
                    fallback_script = self._fallback.register_script(script) if self._fallback else None
                    if fallback_script:
                        return await fallback_script(keys=keys, args=args)
                
                logger.error(f"Redis script execution failed: {type(e).__name__}: {e}")
                raise
        
        return execute_script
    
    # ─────────────────────────────────────────────────────────
    # HASH OPERATIONS (for structured data storage)
    # ─────────────────────────────────────────────────────────
    
    async def hset(self, name: str, key: str = None, value: str = None, mapping: dict = None) -> int:
        """Set hash field(s) with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            if self._use_fallback:
                return await store.hset(name, key, value, mapping)
            if mapping:
                return await store.hset(name, mapping=mapping)
            return await store.hset(name, key, value)
        except Exception as e:
            logger.error(f"Redis HSET failed for {name}: {e}")
            self._enable_fallback()
            return await self._fallback.hset(name, key, value, mapping)
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            return await store.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET failed for {name}.{key}: {e}")
            self._enable_fallback()
            return await self._fallback.hget(name, key)
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all hash fields with fallback handling"""
        await self._check_connection()
        store = self._get_store()
        try:
            return await store.hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL failed for {name}: {e}")
            self._enable_fallback()
            return await self._fallback.hgetall(name)

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

async def get_recent_history(user_id: str, limit: int = 6) -> str:
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

async def get_redis_client():
    """FastAPI dependency to get Redis client singleton"""
    return redis_client
