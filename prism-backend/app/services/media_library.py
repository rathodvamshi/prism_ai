"""
Media Library Service
Manages user's personal media collection with Neo4j storage

🚀 OPTIMIZED with Circuit Breaker pattern for Neo4j failures
"""
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import logging
import time

logger = logging.getLogger(__name__)

# 🔇 Track if Neo4j unavailability has been logged (reduce noise)
_neo4j_unavailable_logged = False

# 🔌 Circuit Breaker State (prevents repeated slow failures)
_circuit_breaker = {
    "state": "closed",  # closed (normal), open (failing fast), half-open (testing)
    "failures": 0,
    "last_failure_time": None,
    "cooldown_seconds": 30,  # How long to wait before retrying after failure
    "failure_threshold": 3   # Number of failures before opening circuit
}


def _is_circuit_open() -> bool:
    """Check if circuit breaker is open (should skip Neo4j calls)"""
    global _circuit_breaker
    
    if _circuit_breaker["state"] == "closed":
        return False
    
    if _circuit_breaker["state"] == "open":
        # Check if cooldown period has passed
        if _circuit_breaker["last_failure_time"]:
            elapsed = time.time() - _circuit_breaker["last_failure_time"]
            if elapsed >= _circuit_breaker["cooldown_seconds"]:
                # Move to half-open state to test connection
                _circuit_breaker["state"] = "half-open"
                logger.info("🔌 Neo4j circuit breaker: half-open (testing connection)")
                return False
        return True
    
    # half-open state - allow one request to test
    return False


def _record_success():
    """Record a successful Neo4j call"""
    global _circuit_breaker
    if _circuit_breaker["state"] != "closed":
        logger.info("✅ Neo4j circuit breaker: closed (connection restored)")
    _circuit_breaker["state"] = "closed"
    _circuit_breaker["failures"] = 0
    _circuit_breaker["last_failure_time"] = None


def _record_failure(error: Exception):
    """Record a failed Neo4j call"""
    global _circuit_breaker, _neo4j_unavailable_logged
    
    _circuit_breaker["failures"] += 1
    _circuit_breaker["last_failure_time"] = time.time()
    
    if _circuit_breaker["failures"] >= _circuit_breaker["failure_threshold"]:
        if _circuit_breaker["state"] != "open":
            logger.warning(f"🔌 Neo4j circuit breaker: OPEN (too many failures, will retry in {_circuit_breaker['cooldown_seconds']}s)")
        _circuit_breaker["state"] = "open"


def _is_neo4j_connection_error(error: Exception) -> bool:
    """Check if error is a Neo4j connection/DNS issue (should be silenced)"""
    error_msg = str(error).lower()
    return any(x in error_msg for x in ["resolve", "getaddrinfo", "connection", "timeout", "unavailable"])


def _log_neo4j_error(context: str, error: Exception):
    """Log Neo4j errors gracefully - silence connection errors after first log"""
    global _neo4j_unavailable_logged
    
    _record_failure(error)
    
    if _is_neo4j_connection_error(error):
        if not _neo4j_unavailable_logged:
            logger.warning(f"⚠️ Neo4j unavailable - media library features disabled")
            _neo4j_unavailable_logged = True
        logger.debug(f"Neo4j unavailable during {context}: {error}")
    else:
        logger.error(f"❌ {context}: {error}")


async def save_to_library(user_id: str, media_data: dict) -> dict:
    """
    Save played media to user's library
    IMPORTANT: Deduplicates by video_id - one entry per user per video
    
    🚀 OPTIMIZED: Circuit breaker prevents slow failures
    
    Args:
        user_id: User's unique ID
        media_data: {video_id, query, title, artist, thumbnail, category}
    
    Returns:
        Saved media object
    """
    from app.db.neo4j_client import get_neo4j_driver
    
    # 🔌 Circuit breaker: Fast fail if Neo4j is known to be down
    if _is_circuit_open():
        logger.debug("Circuit breaker OPEN - skipping media save")
        return {}
    
    driver = get_neo4j_driver()
    
    # Guard: Check if driver is available
    if not driver:
        logger.warning("⚠️ Neo4j driver not available - skipping media save")
        return {}
    
    # Guard: Validate required fields
    video_id = media_data.get("video_id")
    if not video_id or not user_id:
        logger.warning(f"⚠️ Missing required fields: video_id={video_id}, user_id={user_id}")
        return {}
    
    try:
        async with driver.session() as session:
            # Create Media node directly (no User dependency for flexibility)
            result = await session.run("""
                // Use video_id as unique key - no duplicates per user
                MERGE (m:Media {user_id: $user_id, video_id: $video_id})
                ON CREATE SET
                    m.query = $query,
                    m.title = $title,
                    m.artist = $artist,
                    m.thumbnail = $thumbnail,
                    m.category = $category,
                    m.is_favorite = false,
                    m.created_at = datetime(),
                    m.added_at = datetime(),
                    m.last_played_at = datetime(),
                    m.play_count = 1
                ON MATCH SET
                    m.last_played_at = datetime(),
                    m.play_count = COALESCE(m.play_count, 0) + 1,
                    m.title = COALESCE($title, m.title),
                    m.artist = COALESCE($artist, m.artist),
                    m.thumbnail = COALESCE($thumbnail, m.thumbnail)
                
                // Also link to User if exists (optional relationship)
                WITH m
                OPTIONAL MATCH (u:User {id: $user_id})
                FOREACH (_ IN CASE WHEN u IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (u)-[:PLAYED]->(m)
                )
                
                RETURN m, m.play_count as plays, m.last_played_at as last_played
            """, {
                "user_id": user_id,
                "video_id": video_id,
                "query": media_data.get("query", ""),
                "title": media_data.get("title", ""),
                "artist": media_data.get("artist", ""),
                "thumbnail": media_data.get("thumbnail", f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"),
                "category": media_data.get("category", "audio")
            })
            
            record = await result.single()
            if record:
                media = dict(record["m"])
                media["plays"] = record["plays"]
                media["last_played"] = str(record["last_played"])
                logger.info(f"✅ Saved to library: {media.get('title')} (plays: {media['plays']})")
                _record_success()  # Circuit breaker: record success
                return media
            
            _record_success()  # Circuit breaker: record success
            return {}
                
    except Exception as e:
        _log_neo4j_error("Failed to save to library", e)
        return {}


async def get_from_library(user_id: str, query: str) -> Optional[dict]:
    """
    Check if user has played this media before
    Returns cached video_id if found (instant, no scraping needed)
    
    🚀 OPTIMIZED: Circuit breaker prevents slow failures
    """
    from app.db.neo4j_client import get_neo4j_driver
    
    # 🔌 Circuit breaker: Fast fail if Neo4j is known to be down
    if _is_circuit_open():
        logger.debug("Circuit breaker OPEN - skipping library lookup")
        return None
    
    driver = get_neo4j_driver()
    
    # Guard: Check if driver is available
    if not driver:
        logger.warning("⚠️ Neo4j driver not available - skipping library lookup")
        return None
    
    if not user_id or not query:
        return None
    
    try:
        async with driver.session() as session:
            # Search by user_id property on Media node (more reliable)
            result = await session.run("""
                MATCH (m:Media {user_id: $user_id})
                WHERE toLower(m.query) CONTAINS toLower($query)
                   OR toLower(m.title) CONTAINS toLower($query)
                   OR toLower(m.artist) CONTAINS toLower($query)
                RETURN m
                ORDER BY m.last_played_at DESC
                LIMIT 1
            """, {"user_id": user_id, "query": query})
            
            record = await result.single()
            if record:
                media = dict(record["m"])
                logger.info(f"🎯 Found in library: {media.get('title')} - INSTANT REPLAY")
                _record_success()  # Circuit breaker: record success
                return media
            
            _record_success()  # Circuit breaker: record success (query worked, just no results)
                
    except Exception as e:
        _log_neo4j_error("Library lookup failed", e)
    
    return None


async def get_user_library(user_id: str, limit: int = 50, category: Optional[str] = None, favorites_only: bool = False) -> List[dict]:
    """
    Get user's complete media library - OPTIMIZED FOR SPEED
    - Redis cache (5min TTL)
    - Circuit breaker for Neo4j failures
    - Only essential fields returned
    - ORDERED BY: Newest first (added_at DESC)
    
    Args:
        user_id: User's unique ID  
        limit: Max items to return
        category: Filter by category (audio, visual)
        favorites_only: If True, only return favorited items
    
    Returns:
        List of media items (newest first) - FAST!
    """
    from app.db.neo4j_client import get_neo4j_driver
    from app.db.redis_client import redis_client
    import json
    
    # Guard: Validate user_id
    if not user_id:
        logger.warning("⚠️ Missing user_id for get_user_library")
        return []
    
    # 🚀 SPEED: Redis cache key
    cache_key = f"media_library:{user_id}:{category or 'all'}:{favorites_only}:{limit}"
    
    # Check cache first
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            logger.info(f"⚡ Cache HIT for media library (instant)")
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis cache check failed: {e}")
    
    # 🔌 Circuit breaker: Fast fail if Neo4j is known to be down
    if _is_circuit_open():
        logger.debug("Circuit breaker OPEN - returning empty library")
        return []
    
    driver = get_neo4j_driver()
    
    # Guard: Check if driver is available
    if not driver:
        logger.warning("⚠️ Neo4j driver not available - returning empty library")
        return []
    
    try:
        async with driver.session() as session:
            # Build query with filters
            where_clauses = ["m.user_id = $user_id"]  # Always filter by user_id
            if category:
                where_clauses.append("m.category = $category")
            if favorites_only:
                where_clauses.append("m.is_favorite = true")
            
            where_clause = "WHERE " + " AND ".join(where_clauses)
            
            # 🚀 SPEED: Only return essential fields (not full node)
            query = f"""
                MATCH (m:Media)
                {where_clause}
                RETURN 
                    m.video_id as video_id,
                    m.title as title,
                    m.artist as artist,
                    m.query as query,
                    m.thumbnail as thumbnail,
                    m.category as category,
                    m.play_count as plays,
                    m.last_played_at as last_played,
                    m.is_favorite as is_favorite
                ORDER BY m.added_at DESC
                LIMIT $limit
            """
            
            params = {"user_id": user_id, "limit": limit}
            if category:
                params["category"] = category
                
            result = await session.run(query, params)
            
            library = []
            async for record in result:
                video_id = record["video_id"]
                if not video_id:
                    continue  # Skip invalid entries
                    
                library.append({
                    "video_id": video_id,
                    "title": record["title"] or "",
                    "artist": record["artist"] or "",
                    "query": record["query"] or "",
                    "thumbnail": record["thumbnail"] or f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                    "category": record["category"] or "audio",
                    "plays": record["plays"] or 0,
                    "last_played": str(record["last_played"]) if record["last_played"] else "",
                    "is_favorite": bool(record["is_favorite"])
                })
            
            # 🚀 SPEED: Cache result for 5 minutes
            try:
                await redis_client.setex(cache_key, 300, json.dumps(library))
            except Exception as e:
                logger.warning(f"Failed to cache: {e}")
            
            logger.info(f"📚 Retrieved {len(library)} items from library (favorites_only={favorites_only})")
            return library
            
    except Exception as e:
        _log_neo4j_error("Failed to get library", e)
        return []


async def toggle_favorite(user_id: str, video_id: str) -> bool:
    """
    Toggle favorite status for a media item
    is_favorite flag only - no duplication
    
    Args:
        user_id: User's unique ID
        video_id: YouTube video ID
    
    Returns:
        New favorite status (True/False)
    """
    from app.db.neo4j_client import get_neo4j_driver
    from app.db.redis_client import redis_client
    
    # Guard: Validate inputs
    if not user_id or not video_id:
        logger.warning(f"⚠️ Missing required fields for toggle_favorite: user_id={user_id}, video_id={video_id}")
        return False
    
    driver = get_neo4j_driver()
    
    # Guard: Check if driver is available
    if not driver:
        logger.warning("⚠️ Neo4j driver not available - cannot toggle favorite")
        return False
    
    try:
        async with driver.session() as session:
            result = await session.run("""
                MATCH (m:Media {user_id: $user_id, video_id: $video_id})
                SET m.is_favorite = NOT COALESCE(m.is_favorite, false)
                RETURN m.is_favorite as is_favorite
            """, {
                "user_id": user_id,
                "video_id": video_id
            })
            
            record = await result.single()
            if record:
                new_status = bool(record["is_favorite"])
                logger.info(f"{'⭐ Favorited' if new_status else '💔 Unfavorited'}: {video_id}")
                
                # Invalidate cache after toggle
                try:
                    cache_patterns = [
                        f"media_library:{user_id}:*"
                    ]
                    # Simple invalidation - delete all library caches for user
                    for pattern in [f"media_library:{user_id}:all:False:*", 
                                    f"media_library:{user_id}:all:True:*",
                                    f"media_library:{user_id}:audio:*",
                                    f"media_library:{user_id}:visual:*"]:
                        try:
                            keys = await redis_client.keys(pattern)
                            if keys:
                                await redis_client.delete(*keys)
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f"⚠️ Cache invalidation failed: {e}")
                
                return new_status
            
            logger.warning(f"⚠️ Media not found: {video_id} for user {user_id}")
            return False
                
    except Exception as e:
        _log_neo4j_error("Failed to toggle favorite", e)
        return False


async def search_library(user_id: str, search_query: str) -> List[dict]:
    """
    Search user's library with fuzzy matching
    Supports natural language: "that romantic song from yesterday"
    """
    from app.db.neo4j_client import get_neo4j_driver
    
    # Guard: Validate inputs
    if not user_id or not search_query:
        logger.warning(f"⚠️ Missing required fields for search: user_id={user_id}, query={search_query}")
        return []
    
    driver = get_neo4j_driver()
    
    # Guard: Check if driver is available
    if not driver:
        logger.warning("⚠️ Neo4j driver not available - returning empty search results")
        return []
    
    try:
        async with driver.session() as session:
            # Use Media {user_id} pattern (consistent with save_to_library)
            result = await session.run("""
                MATCH (m:Media {user_id: $user_id})
                WHERE toLower(m.query) CONTAINS toLower($query)
                   OR toLower(m.title) CONTAINS toLower($query)
                   OR toLower(m.artist) CONTAINS toLower($query)
                   OR toLower(m.category) CONTAINS toLower($query)
                RETURN m
                ORDER BY m.play_count DESC, m.last_played_at DESC
                LIMIT 10
            """, {"user_id": user_id, "query": search_query})
            
            results = []
            async for record in result:
                media = dict(record["m"])
                results.append(media)
            
            logger.info(f"🔍 Library search for '{search_query}': {len(results)} results")
            return results
            
    except Exception as e:
        _log_neo4j_error("Library search failed", e)
        return []


async def delete_from_library(user_id: str, video_id: str) -> bool:
    """Remove media from user's library"""
    from app.db.neo4j_client import get_neo4j_driver
    from app.db.redis_client import redis_client
    
    # Guard: Validate inputs
    if not user_id or not video_id:
        logger.warning(f"⚠️ Missing required fields for delete: user_id={user_id}, video_id={video_id}")
        return False
    
    driver = get_neo4j_driver()
    
    # Guard: Check if driver is available
    if not driver:
        logger.warning("⚠️ Neo4j driver not available - cannot delete from library")
        return False
    
    try:
        async with driver.session() as session:
            # Use Media {user_id, video_id} pattern (consistent with save_to_library)
            # Also delete any relationships and the node itself
            result = await session.run("""
                MATCH (m:Media {user_id: $user_id, video_id: $video_id})
                DETACH DELETE m
                RETURN count(m) as deleted
            """, {"user_id": user_id, "video_id": video_id})
            
            record = await result.single()
            deleted = record["deleted"] if record else 0
            
            if deleted > 0:
                logger.info(f"🗑️ Removed from library: {video_id}")
                
                # Invalidate cache
                try:
                    for pattern in [f"media_library:{user_id}:all:*", 
                                    f"media_library:{user_id}:audio:*",
                                    f"media_library:{user_id}:visual:*"]:
                        keys = await redis_client.keys(pattern)
                        if keys:
                            await redis_client.delete(*keys)
                except Exception as e:
                    logger.warning(f"⚠️ Cache invalidation failed: {e}")
                
                return True
            else:
                logger.warning(f"⚠️ Media not found for delete: {video_id}")
                return False
            
    except Exception as e:
        _log_neo4j_error("Failed to delete from library", e)
        return False


async def get_library_stats(user_id: str) -> dict:
    """Get user's library statistics"""
    from app.db.neo4j_client import get_neo4j_driver
    
    # Guard: Validate user_id
    if not user_id:
        logger.warning("⚠️ Missing user_id for get_library_stats")
        return {"total_items": 0, "total_plays": 0, "by_category": {}}
    
    driver = get_neo4j_driver()
    
    # Guard: Check if driver is available
    if not driver:
        logger.warning("⚠️ Neo4j driver not available - returning empty stats")
        return {"total_items": 0, "total_plays": 0, "by_category": {}}
    
    try:
        async with driver.session() as session:
            # Use Media {user_id} pattern (consistent with save_to_library)
            result = await session.run("""
                MATCH (m:Media {user_id: $user_id})
                WITH count(m) as total_items, sum(COALESCE(m.play_count, 1)) as total_plays
                MATCH (m2:Media {user_id: $user_id})
                WITH total_items, total_plays, m2.category as category, count(*) as cat_count
                RETURN total_items, total_plays, category, cat_count
                ORDER BY cat_count DESC
            """, {"user_id": user_id})
            
            stats = {
                "total_items": 0,
                "total_plays": 0,
                "by_category": {}
            }
            
            async for record in result:
                stats["total_items"] = record.get("total_items", 0)
                stats["total_plays"] = record.get("total_plays", 0)
                category = record.get("category") or "unknown"
                stats["by_category"][category] = record.get("cat_count", 0)
            
            logger.info(f"📊 Library stats for {user_id}: {stats['total_items']} items, {stats['total_plays']} plays")
            return stats
            
    except Exception as e:
        _log_neo4j_error("Failed to get library stats", e)
        return {"total_items": 0, "total_plays": 0, "by_category": {}}
