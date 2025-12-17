"""
🚀 Redis Caching Service for Highlights & Mini Agents

High-performance caching layer to reduce database queries
and improve response times for frequently accessed data.

Cache Strategy:
- TTL: 300 seconds (5 minutes) for session data
- Invalidation: On create/update/delete operations
- Prefix-based keys for easy management
"""

import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.db.redis_client import redis_client

logger = logging.getLogger(__name__)

class CacheService:
    """High-performance caching for highlights and mini agents"""
    
    # Cache key prefixes
    HIGHLIGHTS_PREFIX = "highlights:"
    MINIAGENTS_PREFIX = "miniagents:"
    MINIAGENT_PREFIX = "miniagent:"
    TASKS_PREFIX = "tasks:"  # NEW: Task list caching
    SESSIONS_PREFIX = "sessions:"  # NEW: Session history caching
    DRAFT_PREFIX = "draft:"  # Part 11: Task drafts
    UI_STATE_PREFIX = "ui:"  # Part 11: Temporary UI state
    LOCK_PREFIX = "lock:"  # Part 11: Session locks
    
    # Cache TTL (5 minutes)
    CACHE_TTL = 300
    # Draft TTL (1 hour - temporary data)
    DRAFT_TTL = 3600
    # Lock TTL (30 seconds - short-lived)
    LOCK_TTL = 30
    
    @staticmethod
    def _serialize_datetime(obj: Any) -> Any:
        """Recursively serialize datetime objects to ISO format"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: CacheService._serialize_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [CacheService._serialize_datetime(item) for item in obj]
        return obj
    
    # ========== HIGHLIGHTS CACHING ==========
    
    @staticmethod
    async def get_highlights(session_id: str) -> Optional[List[Dict]]:
        """Get highlights from cache"""
        try:
            cache_key = f"{CacheService.HIGHLIGHTS_PREFIX}{session_id}"
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"✅ Cache HIT: highlights:{session_id}")
                return json.loads(cached_data)
            
            logger.info(f"❌ Cache MISS: highlights:{session_id}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    @staticmethod
    async def set_highlights(session_id: str, highlights: List[Dict]) -> bool:
        """Cache highlights with TTL"""
        try:
            cache_key = f"{CacheService.HIGHLIGHTS_PREFIX}{session_id}"
            
            # Serialize datetime objects
            serialized_highlights = CacheService._serialize_datetime(highlights)
            
            await redis_client.setex(
                cache_key,
                CacheService.CACHE_TTL,
                json.dumps(serialized_highlights)
            )
            logger.info(f"✅ Cached highlights:{session_id} (TTL: {CacheService.CACHE_TTL}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    @staticmethod
    async def invalidate_highlights(session_id: str) -> bool:
        """Invalidate highlights cache for a session"""
        try:
            cache_key = f"{CacheService.HIGHLIGHTS_PREFIX}{session_id}"
            await redis_client.delete(cache_key)
            logger.info(f"🗑️ Invalidated cache: highlights:{session_id}")
            return True
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return False
    
    # ========== MINI AGENTS CACHING ==========
    
    @staticmethod
    async def get_mini_agents(session_id: str) -> Optional[List[Dict]]:
        """Get mini agents from cache"""
        try:
            cache_key = f"{CacheService.MINIAGENTS_PREFIX}{session_id}"
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"✅ Cache HIT: miniagents:{session_id}")
                return json.loads(cached_data)
            
            logger.info(f"❌ Cache MISS: miniagents:{session_id}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    @staticmethod
    async def set_mini_agents(session_id: str, mini_agents: List[Dict]) -> bool:
        """Cache mini agents with TTL"""
        try:
            cache_key = f"{CacheService.MINIAGENTS_PREFIX}{session_id}"
            
            # Serialize datetime objects
            serialized_agents = CacheService._serialize_datetime(mini_agents)
            
            await redis_client.setex(
                cache_key,
                CacheService.CACHE_TTL,
                json.dumps(serialized_agents)
            )
            logger.info(f"✅ Cached miniagents:{session_id} (TTL: {CacheService.CACHE_TTL}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    @staticmethod
    async def invalidate_mini_agents(session_id: str) -> bool:
        """Invalidate mini agents cache for a session"""
        try:
            cache_key = f"{CacheService.MINIAGENTS_PREFIX}{session_id}"
            await redis_client.delete(cache_key)
            logger.info(f"🗑️ Invalidated cache: miniagents:{session_id}")
            return True
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return False
    
    @staticmethod
    async def get_single_mini_agent(agent_id: str) -> Optional[Dict]:
        """Get single mini agent from cache"""
        try:
            cache_key = f"{CacheService.MINIAGENT_PREFIX}{agent_id}"
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"✅ Cache HIT: miniagent:{agent_id}")
                return json.loads(cached_data)
            
            logger.info(f"❌ Cache MISS: miniagent:{agent_id}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    @staticmethod
    async def set_single_mini_agent(agent_id: str, mini_agent: Dict) -> bool:
        """Cache single mini agent with TTL"""
        try:
            cache_key = f"{CacheService.MINIAGENT_PREFIX}{agent_id}"
            
            # Serialize datetime objects
            serialized_agent = CacheService._serialize_datetime(mini_agent)
            
            await redis_client.setex(
                cache_key,
                CacheService.CACHE_TTL,
                json.dumps(serialized_agent)
            )
            logger.info(f"✅ Cached miniagent:{agent_id} (TTL: {CacheService.CACHE_TTL}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    @staticmethod
    async def invalidate_single_mini_agent(agent_id: str) -> bool:
        """Invalidate single mini agent cache"""
        try:
            cache_key = f"{CacheService.MINIAGENT_PREFIX}{agent_id}"
            await redis_client.delete(cache_key)
            logger.info(f"🗑️ Invalidated cache: miniagent:{agent_id}")
            return True
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return False
    
    # ========== TASKS CACHING (Part 10) ==========
    
    @staticmethod
    async def get_tasks(user_id: str, status: Optional[str] = None) -> Optional[List[Dict]]:
        """Get tasks from cache"""
        try:
            cache_key = f"{CacheService.TASKS_PREFIX}{user_id}:{status or 'all'}"
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"✅ Cache HIT: tasks:{user_id}:{status or 'all'}")
                return json.loads(cached_data)
            
            logger.info(f"❌ Cache MISS: tasks:{user_id}:{status or 'all'}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    @staticmethod
    async def set_tasks(user_id: str, tasks: List[Dict], status: Optional[str] = None) -> bool:
        """Cache tasks with TTL"""
        try:
            cache_key = f"{CacheService.TASKS_PREFIX}{user_id}:{status or 'all'}"
            
            # Serialize datetime objects
            serialized_tasks = CacheService._serialize_datetime(tasks)
            
            await redis_client.setex(
                cache_key,
                CacheService.CACHE_TTL,
                json.dumps(serialized_tasks)
            )
            logger.info(f"✅ Cached tasks:{user_id}:{status or 'all'} (TTL: {CacheService.CACHE_TTL}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    @staticmethod
    async def invalidate_tasks(user_id: str) -> bool:
        """Invalidate all task caches for a user (all statuses)"""
        try:
            # Invalidate all possible task cache keys for user
            keys_to_delete = [
                f"{CacheService.TASKS_PREFIX}{user_id}:all",
                f"{CacheService.TASKS_PREFIX}{user_id}:pending",
                f"{CacheService.TASKS_PREFIX}{user_id}:completed"
            ]
            for key in keys_to_delete:
                await redis_client.delete(key)
            logger.info(f"🗑️ Invalidated task cache for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return False
    
    # ========== SESSIONS CACHING (Part 10) ==========
    
    @staticmethod
    async def get_sessions(user_id: str) -> Optional[List[Dict]]:
        """Get session history from cache"""
        try:
            cache_key = f"{CacheService.SESSIONS_PREFIX}{user_id}"
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"✅ Cache HIT: sessions:{user_id}")
                return json.loads(cached_data)
            
            logger.info(f"❌ Cache MISS: sessions:{user_id}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    @staticmethod
    async def set_sessions(user_id: str, sessions: List[Dict]) -> bool:
        """Cache session history with TTL"""
        try:
            cache_key = f"{CacheService.SESSIONS_PREFIX}{user_id}"
            
            # Serialize datetime objects
            serialized_sessions = CacheService._serialize_datetime(sessions)
            
            await redis_client.setex(
                cache_key,
                CacheService.CACHE_TTL,
                json.dumps(serialized_sessions)
            )
            logger.info(f"✅ Cached sessions:{user_id} (TTL: {CacheService.CACHE_TTL}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    @staticmethod
    async def invalidate_sessions(user_id: str) -> bool:
        """Invalidate session history cache for a user"""
        try:
            cache_key = f"{CacheService.SESSIONS_PREFIX}{user_id}"
            await redis_client.delete(cache_key)
            logger.info(f"🗑️ Invalidated sessions cache for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return False
    
    # ========== BATCH OPERATIONS ==========
    
    @staticmethod
    async def get_session_data(session_id: str) -> Dict[str, Optional[List[Dict]]]:
        """Get both highlights and mini agents in one call (batch operation)"""
        highlights = await CacheService.get_highlights(session_id)
        mini_agents = await CacheService.get_mini_agents(session_id)
        
        return {
            "highlights": highlights,
            "miniAgents": mini_agents
        }
    
    @staticmethod
    async def invalidate_session_data(session_id: str) -> bool:
        """Invalidate all session-related caches"""
        try:
            await CacheService.invalidate_highlights(session_id)
            await CacheService.invalidate_mini_agents(session_id)
            logger.info(f"🗑️ Invalidated all cache for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Batch invalidation error: {e}")
            return False
    
    @staticmethod
    async def invalidate_keys(keys: List[str]) -> bool:
        """Invalidate multiple cache keys at once"""
        try:
            for key in keys:
                # Extract prefix and identifier from key
                if key.startswith("highlights:"):
                    session_id = key.replace("highlights:", "")
                    await CacheService.invalidate_highlights(session_id)
                elif key.startswith("miniagents:"):
                    session_id = key.replace("miniagents:", "")
                    await CacheService.invalidate_mini_agents(session_id)
                elif key.startswith("history:"):
                    # History cache - delete directly
                    await redis_client.delete(key)
                else:
                    # Generic key - delete directly
                    await redis_client.delete(key)
            logger.info(f"🗑️ Invalidated {len(keys)} cache keys")
            return True
        except Exception as e:
            logger.error(f"Batch key invalidation error: {e}")
            return False
    
    # ========== DRAFTS IN REDIS (Part 11) ==========
    
    @staticmethod
    async def save_task_draft(user_id: str, draft_data: Dict) -> bool:
        """
        Save task draft in Redis (never MongoDB).
        🚀 Part 11: Fastest - drafts are temporary UI state.
        """
        try:
            draft_id = draft_data.get("draft_id", f"draft_{datetime.now().timestamp()}")
            cache_key = f"{CacheService.DRAFT_PREFIX}{user_id}:{draft_id}"
            
            serialized_draft = CacheService._serialize_datetime(draft_data)
            
            await redis_client.setex(
                cache_key,
                CacheService.DRAFT_TTL,  # 1 hour TTL
                json.dumps(serialized_draft)
            )
            logger.info(f"✅ Saved task draft: {user_id}:{draft_id}")
            return True
        except Exception as e:
            logger.error(f"Draft save error: {e}")
            return False
    
    @staticmethod
    async def get_task_draft(user_id: str, draft_id: str) -> Optional[Dict]:
        """Get task draft from Redis"""
        try:
            cache_key = f"{CacheService.DRAFT_PREFIX}{user_id}:{draft_id}"
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"✅ Draft retrieved: {user_id}:{draft_id}")
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Draft get error: {e}")
            return None
    
    @staticmethod
    async def delete_task_draft(user_id: str, draft_id: str) -> bool:
        """Delete task draft from Redis"""
        try:
            cache_key = f"{CacheService.DRAFT_PREFIX}{user_id}:{draft_id}"
            await redis_client.delete(cache_key)
            logger.info(f"🗑️ Deleted draft: {user_id}:{draft_id}")
            return True
        except Exception as e:
            logger.error(f"Draft delete error: {e}")
            return False
    
    @staticmethod
    async def get_all_user_drafts(user_id: str) -> List[Dict]:
        """Get all drafts for a user"""
        try:
            pattern = f"{CacheService.DRAFT_PREFIX}{user_id}:*"
            keys = await redis_client.keys(pattern)
            
            drafts = []
            for key in keys:
                data = await redis_client.get(key)
                if data:
                    drafts.append(json.loads(data))
            
            return drafts
        except Exception as e:
            logger.error(f"Get all drafts error: {e}")
            return []
    
    # ========== UI STATE MANAGEMENT (Part 11) ==========
    
    @staticmethod
    async def save_ui_state(user_id: str, state_key: str, state_data: Dict) -> bool:
        """
        Save temporary UI state in Redis.
        🚀 Part 11: Never store UI state in MongoDB - it's temporary!
        """
        try:
            cache_key = f"{CacheService.UI_STATE_PREFIX}{user_id}:{state_key}"
            
            serialized_state = CacheService._serialize_datetime(state_data)
            
            await redis_client.setex(
                cache_key,
                CacheService.DRAFT_TTL,  # 1 hour TTL
                json.dumps(serialized_state)
            )
            logger.info(f"✅ Saved UI state: {user_id}:{state_key}")
            return True
        except Exception as e:
            logger.error(f"UI state save error: {e}")
            return False
    
    @staticmethod
    async def get_ui_state(user_id: str, state_key: str) -> Optional[Dict]:
        """Get UI state from Redis"""
        try:
            cache_key = f"{CacheService.UI_STATE_PREFIX}{user_id}:{state_key}"
            
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"UI state get error: {e}")
            return None
    
    # ========== SESSION LOCKS (Part 11) ==========
    
    @staticmethod
    async def acquire_session_lock(session_id: str, user_id: str) -> bool:
        """
        Acquire a lock on a session to prevent concurrent modifications.
        🚀 Part 11: Short-lived locks (30s) for race condition prevention.
        """
        try:
            cache_key = f"{CacheService.LOCK_PREFIX}session:{session_id}"
            
            # Use SET NX (set if not exists) for atomic lock acquisition
            result = await redis_client.set(
                cache_key,
                user_id,
                ex=CacheService.LOCK_TTL,  # 30 second TTL
                nx=True  # Only set if not exists
            )
            
            if result:
                logger.info(f"🔒 Lock acquired: session:{session_id} by {user_id}")
            return bool(result)
        except Exception as e:
            logger.error(f"Lock acquire error: {e}")
            return False
    
    @staticmethod
    async def release_session_lock(session_id: str, user_id: str) -> bool:
        """Release session lock (only if owned by this user)"""
        try:
            cache_key = f"{CacheService.LOCK_PREFIX}session:{session_id}"
            
            # Check ownership before releasing
            current_owner = await redis_client.get(cache_key)
            if current_owner == user_id:
                await redis_client.delete(cache_key)
                logger.info(f"🔓 Lock released: session:{session_id} by {user_id}")
                return True
            else:
                logger.warning(f"⚠️ Lock release failed: {user_id} does not own lock on {session_id}")
                return False
        except Exception as e:
            logger.error(f"Lock release error: {e}")
            return False
    
    @staticmethod
    async def check_session_lock(session_id: str) -> Optional[str]:
        """Check if session is locked and return owner"""
        try:
            cache_key = f"{CacheService.LOCK_PREFIX}session:{session_id}"
            owner = await redis_client.get(cache_key)
            return owner
        except Exception as e:
            logger.error(f"Lock check error: {e}")
            return None
    
    # ========== HEALTH CHECK ==========
    
    @staticmethod
    async def health_check() -> bool:
        """Check if Redis is available"""
        try:
            await redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Singleton instance
cache_service = CacheService()
