"""
⏱️ Service Timeout Utilities
Fail fast - never block the user waiting for slow services.

CRITICAL: All service calls must have timeouts
- Redis: 100-200ms (cache should be instant)
- MongoDB: 300ms (database queries)
- Neo4j: 500ms (graph queries)
- Pinecone: 800ms (vector search)

If timeout: Skip it, return response anyway, log warning
"""

import asyncio
import logging
from typing import Optional, Callable, Any, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ServiceTimeoutError(Exception):
    """Raised when a service call times out"""
    pass


async def with_timeout(
    coro,
    timeout_ms: int,
    service_name: str,
    fallback: Any = None,
    raise_on_timeout: bool = False
) -> Any:
    """
    Execute async function with timeout.
    
    Args:
        coro: Coroutine to execute
        timeout_ms: Timeout in milliseconds
        service_name: Name for logging (e.g., "Redis", "Neo4j")
        fallback: Value to return on timeout (default: None)
        raise_on_timeout: If True, raise ServiceTimeoutError; if False, return fallback
    
    Returns:
        Result of coro if successful, fallback if timeout
    
    Example:
        result = await with_timeout(
            redis_client.get("key"),
            timeout_ms=100,
            service_name="Redis",
            fallback={}
        )
    """
    timeout_seconds = timeout_ms / 1000.0
    
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_seconds)
        return result
    except asyncio.TimeoutError:
        logger.warning(
            f"⏱️ {service_name} timeout after {timeout_ms}ms - using fallback"
        )
        if raise_on_timeout:
            raise ServiceTimeoutError(f"{service_name} timeout after {timeout_ms}ms")
        return fallback
    except Exception as e:
        logger.error(f"❌ {service_name} error: {e}")
        if raise_on_timeout:
            raise
        return fallback


def timeout_decorator(timeout_ms: int, service_name: str, fallback: Any = None):
    """
    Decorator to add timeout to async functions.
    
    Usage:
        @timeout_decorator(timeout_ms=100, service_name="Redis", fallback={})
        async def get_from_redis(key: str):
            return await redis.get(key)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await with_timeout(
                func(*args, **kwargs),
                timeout_ms=timeout_ms,
                service_name=service_name,
                fallback=fallback
            )
        return wrapper
    return decorator


class TimeoutConfig:
    """Service timeout configurations (in milliseconds)"""
    
    # Cache should be instant
    REDIS_GET = 100
    REDIS_SET = 150
    REDIS_DELETE = 100
    
    # Database queries
    MONGODB_FIND = 300
    MONGODB_INSERT = 300
    MONGODB_UPDATE = 300
    MONGODB_DELETE = 300
    
    # Graph database
    NEO4J_READ = 500
    NEO4J_WRITE = 600
    
    # Vector search (slowest)
    PINECONE_SEARCH = 800
    PINECONE_UPSERT = 1000
    
    # External APIs
    LLM_REQUEST = 30000  # 30s for LLM responses (streaming)
    WEB_SEARCH = 5000    # 5s for web searches


# Convenience functions for common operations

async def redis_get_with_timeout(redis_client, key: str, fallback: Any = None) -> Any:
    """Get from Redis with timeout"""
    return await with_timeout(
        redis_client.get(key),
        timeout_ms=TimeoutConfig.REDIS_GET,
        service_name="Redis GET",
        fallback=fallback
    )


async def redis_set_with_timeout(
    redis_client,
    key: str,
    value: Any,
    ex: Optional[int] = None
) -> bool:
    """Set in Redis with timeout"""
    result = await with_timeout(
        redis_client.set(key, value, ex=ex),
        timeout_ms=TimeoutConfig.REDIS_SET,
        service_name="Redis SET",
        fallback=False
    )
    return bool(result)


async def mongodb_find_with_timeout(
    collection,
    query: dict,
    fallback: Any = None
) -> Any:
    """Find in MongoDB with timeout"""
    return await with_timeout(
        collection.find_one(query),
        timeout_ms=TimeoutConfig.MONGODB_FIND,
        service_name="MongoDB FIND",
        fallback=fallback
    )


async def neo4j_query_with_timeout(
    neo4j_func,
    *args,
    fallback: Any = None,
    **kwargs
) -> Any:
    """Execute Neo4j query with timeout"""
    return await with_timeout(
        neo4j_func(*args, **kwargs),
        timeout_ms=TimeoutConfig.NEO4J_READ,
        service_name="Neo4j QUERY",
        fallback=fallback
    )


async def pinecone_search_with_timeout(
    pinecone_func,
    *args,
    fallback: Any = None,
    **kwargs
) -> Any:
    """Execute Pinecone search with timeout"""
    return await with_timeout(
        pinecone_func(*args, **kwargs),
        timeout_ms=TimeoutConfig.PINECONE_SEARCH,
        service_name="Pinecone SEARCH",
        fallback=fallback
    )


class ServiceHealthTracker:
    """
    Track service health based on timeout patterns.
    If a service times out frequently, we can:
    1. Increase timeout
    2. Skip it temporarily
    3. Alert developers
    """
    
    def __init__(self):
        self.timeout_counts = {}
        self.success_counts = {}
    
    def record_timeout(self, service_name: str):
        """Record a timeout for a service"""
        self.timeout_counts[service_name] = self.timeout_counts.get(service_name, 0) + 1
        
        # Log if timeout rate is high
        total = self.timeout_counts[service_name] + self.success_counts.get(service_name, 0)
        if total > 10:
            timeout_rate = self.timeout_counts[service_name] / total
            if timeout_rate > 0.3:  # 30% timeout rate
                logger.warning(
                    f"⚠️ {service_name} has high timeout rate: {timeout_rate:.1%} "
                    f"({self.timeout_counts[service_name]}/{total})"
                )
    
    def record_success(self, service_name: str):
        """Record a successful call"""
        self.success_counts[service_name] = self.success_counts.get(service_name, 0) + 1
    
    def get_health(self, service_name: str) -> dict:
        """Get health metrics for a service"""
        timeouts = self.timeout_counts.get(service_name, 0)
        successes = self.success_counts.get(service_name, 0)
        total = timeouts + successes
        
        if total == 0:
            return {"status": "unknown", "timeout_rate": 0, "total_calls": 0}
        
        timeout_rate = timeouts / total
        
        if timeout_rate < 0.05:
            status = "healthy"
        elif timeout_rate < 0.2:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "timeout_rate": timeout_rate,
            "timeouts": timeouts,
            "successes": successes,
            "total_calls": total
        }
    
    def get_report(self) -> dict:
        """Get health report for all services"""
        all_services = set(self.timeout_counts.keys()) | set(self.success_counts.keys())
        report = {}
        
        for service in all_services:
            timeouts = self.timeout_counts.get(service, 0)
            successes = self.success_counts.get(service, 0)
            total = timeouts + successes
            
            report[service] = {
                "total_calls": total,
                "timeouts": timeouts,
                "successes": successes,
                "timeout_rate": timeouts / total if total > 0 else 0
            }
        
        return report


# Global health tracker
health_tracker = ServiceHealthTracker()


async def tracked_timeout(
    coro,
    timeout_ms: int,
    service_name: str,
    fallback: Any = None
) -> Any:
    """
    Execute with timeout and track health metrics.
    
    Use this instead of with_timeout for production code.
    """
    try:
        result = await with_timeout(
            coro,
            timeout_ms=timeout_ms,
            service_name=service_name,
            fallback=fallback,
            raise_on_timeout=True
        )
        health_tracker.record_success(service_name)
        return result
    except ServiceTimeoutError:
        health_tracker.record_timeout(service_name)
        logger.warning(f"⏱️ {service_name} timeout - using fallback")
        return fallback
    except Exception as e:
        logger.error(f"❌ {service_name} error: {e}")
        return fallback
