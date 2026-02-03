"""
⚡ GROQ API KEY POOL - Ultra-Fast Load Balancer
================================================

Manages multiple Groq API keys with:
- Round-robin + least-used selection (< 1ms)
- Real-time rate tracking in Redis
- Instant failover on errors
- Zero-overhead key selection

Capacity: 5 keys × 30 req/min = 150 req/min = 2000+ users
"""

import asyncio
import time
import logging
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, field
from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)

# ============ CONSTANTS ============
DEFAULT_RATE_LIMIT = 30  # requests per minute per key
UNHEALTHY_COOLDOWN = 60  # seconds to wait before re-enabling a key
RATE_LIMIT_COOLDOWN = 60  # seconds to wait after rate limit
ERROR_COOLDOWN = 30  # seconds to wait after other errors
USAGE_KEY_TTL = 120  # seconds for usage counter TTL


# ============ REDIS HELPER ============
def get_redis():
    """Get Redis client singleton from the database module"""
    try:
        from app.db.redis_client import redis_client
        return redis_client
    except Exception as e:
        logger.error(f"❌ Failed to get Redis client: {e}")
        return None


async def redis_mget(redis, keys: List[str]) -> List[Optional[str]]:
    """Batch get multiple keys (RedisClient doesn't have mget, so we use gather)"""
    if not redis:
        return [None] * len(keys)
    try:
        results = await asyncio.gather(*[redis.get(key) for key in keys], return_exceptions=True)
        return [r if not isinstance(r, Exception) else None for r in results]
    except Exception as e:
        logger.warning(f"⚠️ Redis mget failed: {e}")
        return [None] * len(keys)

# ============ CONFIGURATION ============

@dataclass
class GroqKeyConfig:
    """Configuration for a single Groq API key"""
    key: str
    index: int
    label: str
    rate_limit: int = DEFAULT_RATE_LIMIT
    is_healthy: bool = True
    last_error_time: float = field(default=0.0)
    error_count: int = field(default=0)


class GroqKeyPool:
    """
    Ultra-fast Groq API key pool manager.
    
    Features:
    - Least-used key selection (load balancing)
    - Redis-based rate tracking (sub-millisecond)
    - Automatic failover on errors
    - Health tracking per key
    - Graceful degradation when Redis unavailable
    """
    
    def __init__(self):
        self.keys: List[GroqKeyConfig] = []
        self.clients: Dict[int, AsyncGroq] = {}
        self._initialized = False
        self._lock = asyncio.Lock()
        self._last_key_index = -1  # For round-robin fallback
    
    async def initialize(self) -> None:
        """Initialize pool with platform Groq keys from settings"""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:
                return
            
            # Load keys from environment/settings
            # Format: GROQ_API_KEYS=key1,key2,key3,key4,key5
            # Or individual: GROQ_API_KEY_1, GROQ_API_KEY_2, etc.
            
            keys_str = getattr(settings, 'GROQ_API_KEYS', None) or ""
            
            if keys_str.strip():
                # Multiple keys in comma-separated format
                raw_keys = [k.strip() for k in keys_str.split(',') if k.strip() and k.strip().startswith('gsk_')]
            else:
                # Try individual key settings + main key
                raw_keys = []
                
                # Main key (always include if exists and valid)
                main_key = getattr(settings, 'GROQ_API_KEY', None) or ""
                if main_key.strip() and main_key.strip().startswith('gsk_'):
                    raw_keys.append(main_key.strip())
                
                # Additional keys (GROQ_API_KEY_2 through GROQ_API_KEY_5)
                for i in range(2, 6):
                    key = getattr(settings, f'GROQ_API_KEY_{i}', None) or ""
                    if key.strip() and key.strip().startswith('gsk_'):
                        raw_keys.append(key.strip())
            
            # Create key configs and clients
            for idx, key in enumerate(raw_keys):
                config = GroqKeyConfig(
                    key=key,
                    index=idx,
                    label=f"Platform Key #{idx + 1}"
                )
                self.keys.append(config)
                self.clients[idx] = AsyncGroq(api_key=key)
            
            self._initialized = True
            logger.info(f"⚡ Groq Pool initialized with {len(self.keys)} keys (capacity: {len(self.keys) * 30} req/min)")
    
    async def get_best_key(self) -> Tuple[Optional[GroqKeyConfig], Optional[AsyncGroq]]:
        """
        Get the best available key using least-used strategy.
        Time complexity: O(n) where n = number of keys (max 5)
        Redis calls: n GETs (batched via asyncio.gather)
        
        Returns: (key_config, client) or (None, None) if all exhausted
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.keys:
            logger.error("❌ No Groq API keys configured!")
            return None, None
        
        try:
            redis = get_redis()
            current_minute = int(time.time() // 60)
            current_time = time.time()
            
            # Batch get all key usages (using our helper since RedisClient lacks mget)
            usage_keys = [f"groq_pool:usage:{k.index}:{current_minute}" for k in self.keys]
            usages = await redis_mget(redis, usage_keys)
            
            # Find healthy key with lowest usage
            best_key = None
            best_client = None
            lowest_usage = float('inf')
            
            for idx, (config, usage_str) in enumerate(zip(self.keys, usages)):
                # Skip unhealthy keys (but check if cooldown expired)
                if not config.is_healthy:
                    # Auto-recover after cooldown
                    if current_time - config.last_error_time > UNHEALTHY_COOLDOWN:
                        config.is_healthy = True
                        config.error_count = 0
                        logger.info(f"✅ Key #{config.index + 1} auto-recovered after cooldown")
                    else:
                        continue
                    
                usage = int(usage_str) if usage_str else 0
                
                # Skip if at rate limit
                if usage >= config.rate_limit:
                    continue
                
                if usage < lowest_usage:
                    lowest_usage = usage
                    best_key = config
                    best_client = self.clients[config.index]
            
            if best_key:
                logger.debug(f"⚡ Selected Key #{best_key.index + 1} (usage: {lowest_usage}/{best_key.rate_limit})")
                return best_key, best_client
            
            # All keys exhausted - try round-robin fallback for any healthy key
            logger.warning("⚠️ All Groq keys at rate limit! Trying round-robin fallback...")
            
            # Round-robin: try each key in sequence
            for i in range(len(self.keys)):
                self._last_key_index = (self._last_key_index + 1) % len(self.keys)
                config = self.keys[self._last_key_index]
                if config.is_healthy:
                    logger.info(f"🔄 Round-robin fallback to Key #{config.index + 1}")
                    return config, self.clients[config.index]
            
            return None, None
            
        except Exception as e:
            logger.error(f"❌ Error selecting key: {e}")
            # Fallback to round-robin on any healthy key
            for i in range(len(self.keys)):
                self._last_key_index = (self._last_key_index + 1) % len(self.keys)
                config = self.keys[self._last_key_index]
                if config.is_healthy:
                    return config, self.clients[config.index]
            # Last resort: return first key regardless of health
            if self.keys:
                logger.warning("⚠️ All keys unhealthy, using first key as last resort")
                return self.keys[0], self.clients[0]
            return None, None
    
    async def increment_usage(self, key_index: int) -> None:
        """Increment usage counter for a key (call after successful request)"""
        try:
            redis = get_redis()
            if not redis:
                return  # Skip if Redis unavailable
            
            current_minute = int(time.time() // 60)
            usage_key = f"groq_pool:usage:{key_index}:{current_minute}"
            
            # Increment counter
            await redis.incr(usage_key)
            # Set expiry (2 minutes to handle edge cases)
            await redis.expire(usage_key, USAGE_KEY_TTL)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to increment usage: {e}")
    
    async def mark_unhealthy(self, key_index: int, duration_seconds: int = UNHEALTHY_COOLDOWN) -> None:
        """Temporarily mark a key as unhealthy (e.g., after error)"""
        try:
            for config in self.keys:
                if config.index == key_index:
                    config.is_healthy = False
                    config.last_error_time = time.time()
                    config.error_count += 1
                    logger.warning(f"⚠️ Key #{key_index + 1} marked unhealthy for {duration_seconds}s")
                    
                    # Schedule re-enable
                    asyncio.create_task(self._reenable_key(key_index, duration_seconds))
                    break
        except Exception as e:
            logger.error(f"❌ Error marking key unhealthy: {e}")
    
    async def _reenable_key(self, key_index: int, delay: int) -> None:
        """Re-enable a key after delay"""
        try:
            await asyncio.sleep(delay)
            for config in self.keys:
                if config.index == key_index:
                    config.is_healthy = True
                    logger.info(f"✅ Key #{key_index + 1} re-enabled")
                    break
        except asyncio.CancelledError:
            pass  # Task was cancelled, ignore
        except Exception as e:
            logger.warning(f"⚠️ Error re-enabling key: {e}")
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get current status of all keys in pool"""
        if not self._initialized:
            await self.initialize()
        
        try:
            redis = get_redis()
            current_minute = int(time.time() // 60)
            current_time = time.time()
            
            status = {
                "total_keys": len(self.keys),
                "total_capacity": len(self.keys) * DEFAULT_RATE_LIMIT,
                "redis_available": redis is not None,
                "keys": []
            }
            
            for config in self.keys:
                usage = 0
                if redis:
                    usage_key = f"groq_pool:usage:{config.index}:{current_minute}"
                    usage_val = await redis.get(usage_key)
                    usage = int(usage_val) if usage_val else 0
                
                # Calculate time until auto-recovery
                time_until_recovery = 0
                if not config.is_healthy:
                    time_until_recovery = max(0, UNHEALTHY_COOLDOWN - (current_time - config.last_error_time))
                
                status["keys"].append({
                    "index": config.index,
                    "label": config.label,
                    "usage": usage,
                    "limit": config.rate_limit,
                    "available": max(0, config.rate_limit - usage),
                    "is_healthy": config.is_healthy,
                    "error_count": config.error_count,
                    "time_until_recovery": round(time_until_recovery, 1)
                })
            
            status["total_available"] = sum(k["available"] for k in status["keys"] if k["is_healthy"])
            status["healthy_keys"] = sum(1 for k in status["keys"] if k["is_healthy"])
            return status
            
        except Exception as e:
            logger.error(f"❌ Error getting pool status: {e}")
            return {
                "error": str(e),
                "total_keys": len(self.keys),
                "healthy_keys": sum(1 for k in self.keys if k.is_healthy)
            }


# ============ SINGLETON INSTANCE ============
_pool: Optional[GroqKeyPool] = None
_pool_lock = asyncio.Lock()


async def get_groq_pool() -> GroqKeyPool:
    """Get the global Groq key pool instance (thread-safe)"""
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:  # Double-check after acquiring lock
                _pool = GroqKeyPool()
                await _pool.initialize()
    return _pool


# ============ STREAMING HELPER ============
async def stream_with_pool(
    messages: List[Dict[str, str]],
    model: str = "llama-3.1-8b-instant",
    max_tokens: int = 2048,
    temperature: float = 0.7,
    user_api_key: Optional[str] = None
):
    """
    Stream response using the key pool with automatic failover.
    
    Args:
        messages: Chat messages
        model: Model to use
        max_tokens: Max tokens in response
        temperature: Response temperature
        user_api_key: User's own key (highest priority)
    
    Yields:
        Response chunks
    """
    pool = await get_groq_pool()
    
    # If user has their own key, use it (no pool overhead)
    if user_api_key and user_api_key.startswith('gsk_'):
        client = AsyncGroq(api_key=user_api_key)
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            async for chunk in response:
                # Safe null checks for chunk.choices
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
            return
        except Exception as e:
            logger.warning(f"⚠️ User key failed: {e}, falling back to pool")
    
    # Use pool with failover
    attempts = 0
    max_attempts = max(len(pool.keys), 1) if pool.keys else 1
    last_error = None
    
    while attempts < max_attempts:
        key_config, client = await pool.get_best_key()
        
        if not key_config or not client:
            break
        
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            
            # Increment usage on success
            await pool.increment_usage(key_config.index)
            
            async for chunk in response:
                # Safe null checks for chunk.choices
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
            
            return  # Success - exit
            
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            # Check if rate limit error
            if "rate" in error_str or "limit" in error_str or "429" in error_str:
                logger.warning(f"⚠️ Key #{key_config.index + 1} rate limited, trying next...")
                await pool.mark_unhealthy(key_config.index, duration_seconds=RATE_LIMIT_COOLDOWN)
            else:
                logger.error(f"❌ Key #{key_config.index + 1} error: {e}")
                await pool.mark_unhealthy(key_config.index, duration_seconds=ERROR_COOLDOWN)
            
            attempts += 1
    
    # All keys failed
    error_msg = f"All {max_attempts} Groq keys exhausted. Last error: {last_error}"
    logger.error(f"❌ {error_msg}")
    raise Exception(error_msg)


# ============ NON-STREAMING HELPER ============
async def complete_with_pool(
    messages: List[Dict[str, str]],
    model: str = "llama-3.1-8b-instant",
    max_tokens: int = 2048,
    temperature: float = 0.7,
    user_api_key: Optional[str] = None
) -> str:
    """
    Get completion using the key pool with automatic failover.
    Non-streaming version for quick internal calls.
    
    Returns:
        Response content string, or empty string on failure
    """
    pool = await get_groq_pool()
    
    # If user has their own key, use it
    if user_api_key and user_api_key.startswith('gsk_'):
        client = AsyncGroq(api_key=user_api_key)
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            # Safe null checks
            if response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                if message and message.content:
                    return message.content
            return ""
        except Exception as e:
            logger.warning(f"⚠️ User key failed: {e}, falling back to pool")
    
    # Use pool with failover
    attempts = 0
    max_attempts = max(len(pool.keys), 1) if pool.keys else 1
    last_error = None
    
    while attempts < max_attempts:
        key_config, client = await pool.get_best_key()
        
        if not key_config or not client:
            break
        
        try:
            # Increment usage first (optimistic)
            await pool.increment_usage(key_config.index)
            
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            
            # Safe null checks
            if response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                if message and message.content:
                    return message.content
            return ""
            
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            if "rate" in error_str or "limit" in error_str or "429" in error_str:
                await pool.mark_unhealthy(key_config.index, duration_seconds=RATE_LIMIT_COOLDOWN)
            else:
                await pool.mark_unhealthy(key_config.index, duration_seconds=ERROR_COOLDOWN)
            
            attempts += 1
    
    raise Exception(f"All Groq keys exhausted. Last error: {last_error}")
