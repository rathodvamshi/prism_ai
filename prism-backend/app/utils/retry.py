"""
🚀 Part 18: Smart Retry Logic with Exponential Backoff

Retry strategy for DB and memory operations:
- Max 1-2 retries only
- Exponential backoff (50ms, 200ms)
- Fail silently after max retries
- NO infinite retries

Usage:
    result = await smart_retry(
        operation=lambda: db.find_one({"_id": id}),
        operation_name="MongoDB find_one",
        max_retries=2
    )
"""

import asyncio
import logging
from typing import Callable, Any, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def smart_retry(
    operation: Callable[[], Any],
    operation_name: str,
    max_retries: int = 2,
    base_delay_ms: int = 50,
    fail_silently: bool = True,
    fallback: Optional[T] = None
) -> Optional[T]:
    """
    🚀 Part 18: Smart retry with exponential backoff.
    
    Args:
        operation: Async function to retry
        operation_name: Name for logging (e.g., "MongoDB query")
        max_retries: Maximum retry attempts (default: 2)
        base_delay_ms: Base delay in milliseconds (default: 50ms)
        fail_silently: If True, return fallback on failure; if False, raise
        fallback: Value to return on failure (default: None)
    
    Returns:
        Result from operation, or fallback on failure
    
    Example:
        # MongoDB query with retry
        user = await smart_retry(
            operation=lambda: users_collection.find_one({"_id": user_id}),
            operation_name="MongoDB find user",
            max_retries=2
        )
        
        # Redis get with fallback
        cached = await smart_retry(
            operation=lambda: redis_client.get(key),
            operation_name="Redis GET",
            fallback={},
            max_retries=1
        )
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            result = await operation()
            
            # Log recovery if this was a retry
            if attempt > 0:
                logger.info(f"✅ {operation_name} succeeded on attempt {attempt + 1}")
            
            return result
            
        except Exception as e:
            last_error = e
            
            # Last attempt - don't retry
            if attempt >= max_retries:
                if fail_silently:
                    logger.warning(
                        f"⚠️ {operation_name} failed after {max_retries} retries. "
                        f"Failing silently. Error: {str(e)[:100]}"
                    )
                    return fallback
                else:
                    logger.error(f"❌ {operation_name} failed after {max_retries} retries: {e}")
                    raise
            
            # Calculate exponential backoff delay
            delay_ms = base_delay_ms * (2 ** attempt)
            delay_sec = delay_ms / 1000
            
            logger.warning(
                f"⚠️ {operation_name} failed (attempt {attempt + 1}/{max_retries + 1}). "
                f"Retrying in {delay_ms}ms... Error: {str(e)[:100]}"
            )
            
            await asyncio.sleep(delay_sec)
    
    # Should never reach here, but for type safety
    return fallback


async def smart_retry_sync(
    operation: Callable[[], Any],
    operation_name: str,
    max_retries: int = 2,
    base_delay_ms: int = 50,
    fail_silently: bool = True,
    fallback: Optional[T] = None
) -> Optional[T]:
    """
    🚀 Part 18: Smart retry for SYNCHRONOUS operations.
    
    Same as smart_retry() but for sync functions.
    Wraps sync operations with asyncio.to_thread() for non-blocking execution.
    
    Example:
        # Synchronous Neo4j query with retry
        result = await smart_retry_sync(
            operation=lambda: neo4j_session.run(query).single(),
            operation_name="Neo4j query",
            max_retries=2
        )
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            # Run sync operation in thread pool to avoid blocking
            result = await asyncio.to_thread(operation)
            
            if attempt > 0:
                logger.info(f"✅ {operation_name} succeeded on attempt {attempt + 1}")
            
            return result
            
        except Exception as e:
            last_error = e
            
            if attempt >= max_retries:
                if fail_silently:
                    logger.warning(
                        f"⚠️ {operation_name} failed after {max_retries} retries. "
                        f"Failing silently. Error: {str(e)[:100]}"
                    )
                    return fallback
                else:
                    logger.error(f"❌ {operation_name} failed after {max_retries} retries: {e}")
                    raise
            
            delay_ms = base_delay_ms * (2 ** attempt)
            delay_sec = delay_ms / 1000
            
            logger.warning(
                f"⚠️ {operation_name} failed (attempt {attempt + 1}/{max_retries + 1}). "
                f"Retrying in {delay_ms}ms... Error: {str(e)[:100]}"
            )
            
            await asyncio.sleep(delay_sec)
    
    return fallback


# ========== CONVENIENCE WRAPPERS FOR COMMON OPERATIONS ==========

async def retry_mongodb(operation: Callable[[], Any], operation_name: str = "MongoDB") -> Optional[Any]:
    """Retry MongoDB operation with 2 attempts"""
    return await smart_retry(
        operation=operation,
        operation_name=operation_name,
        max_retries=2,
        base_delay_ms=50,
        fail_silently=True,
        fallback=None
    )


async def retry_redis(operation: Callable[[], Any], operation_name: str = "Redis") -> Optional[Any]:
    """Retry Redis operation with 1 attempt (fast fail)"""
    return await smart_retry(
        operation=operation,
        operation_name=operation_name,
        max_retries=1,
        base_delay_ms=50,
        fail_silently=True,
        fallback=None
    )


async def retry_neo4j(operation: Callable[[], Any], operation_name: str = "Neo4j") -> Optional[Any]:
    """Retry Neo4j operation with 2 attempts"""
    return await smart_retry_sync(  # Neo4j uses sync operations
        operation=operation,
        operation_name=operation_name,
        max_retries=2,
        base_delay_ms=100,
        fail_silently=True,
        fallback=None
    )


async def retry_pinecone(operation: Callable[[], Any], operation_name: str = "Pinecone") -> Optional[Any]:
    """Retry Pinecone operation with 1 attempt (fast fail, optional service)"""
    return await smart_retry(
        operation=operation,
        operation_name=operation_name,
        max_retries=1,
        base_delay_ms=100,
        fail_silently=True,
        fallback=None
    )


# ========== USAGE EXAMPLES ==========

"""
Example 1: MongoDB query with retry

    from app.utils.retry import smart_retry
    
    async def get_user(user_id: str):
        user = await smart_retry(
            operation=lambda: users_collection.find_one({"_id": ObjectId(user_id)}),
            operation_name=f"MongoDB find user {user_id}",
            max_retries=2
        )
        return user if user else None


Example 2: Redis cache with fallback

    from app.utils.retry import smart_retry
    
    async def get_cached_tasks(user_id: str):
        cached = await smart_retry(
            operation=lambda: redis_client.get(f"tasks:{user_id}"),
            operation_name="Redis GET tasks",
            fallback=[],
            max_retries=1
        )
        return json.loads(cached) if cached else []


Example 3: Neo4j graph query

    from app.utils.retry import smart_retry_sync
    
    async def get_relationships(user_id: str):
        def neo4j_query():
            with neo4j_driver.session() as session:
                result = session.run(
                    "MATCH (u:User {id: $user_id})-[r]->(n) RETURN r, n",
                    user_id=user_id
                )
                return [record for record in result]
        
        relationships = await smart_retry_sync(
            operation=neo4j_query,
            operation_name="Neo4j get relationships",
            max_retries=2
        )
        return relationships if relationships else []


Example 4: Pinecone vector search

    from app.utils.retry import retry_pinecone
    
    async def search_vectors(query_vector: list):
        results = await retry_pinecone(
            operation=lambda: pinecone_index.query(
                vector=query_vector,
                top_k=10
            ),
            operation_name="Pinecone vector search"
        )
        return results.get("matches", []) if results else []


Example 5: Batch retry with different strategies

    from app.utils.retry import retry_mongodb, retry_redis, retry_neo4j
    
    async def load_user_context(user_id: str):
        # Critical: MongoDB with 2 retries
        user = await retry_mongodb(
            lambda: users_collection.find_one({"_id": user_id}),
            "Load user"
        )
        
        # Fast: Redis with 1 retry
        cache = await retry_redis(
            lambda: redis_client.get(f"user:{user_id}"),
            "Load cache"
        )
        
        # Optional: Neo4j with 2 retries
        graph = await retry_neo4j(
            lambda: neo4j_client.get_relationships(user_id),
            "Load graph"
        )
        
        return {
            "user": user,
            "cache": json.loads(cache) if cache else {},
            "graph": graph if graph else []
        }
"""
