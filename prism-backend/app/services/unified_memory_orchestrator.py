"""
🧠 UNIFIED MEMORY ORCHESTRATOR - PRODUCTION READY
=================================================

CRITICAL BEHAVIOR (NON-NEGOTIABLE):

1. Memory Fetch Order (Stop-on-Hit):
   Redis (session) → MongoDB (structured) → Neo4j (graph) → Pinecone (semantic)
   ⚠️ STOP searching the moment relevant memory is found

2. Master Prompt Enrichment:
   - Inject found memory into [SYSTEM MEMORY CONTEXT]
   - Label memory source clearly
   - Never hallucinate or reuse stale data

3. Memory Storage Rules:
   - Store only when needed (no duplicates, no noise)
   - Choose correct system based on memory type
   - Confirm successful write with logs

4. Debug Visibility:
   - Log EVERY fetch decision (why/what/result)
   - Log EVERY storage decision (why/what/where)
   - Enable end-to-end pipeline tracing

5. Pipeline Flow:
   User Input → Intent Detection → Memory Required? → 
   Fetch (stop-on-hit) → Enrich Prompt → Model Response → 
   Store Decision → Persist Memory
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MemorySource(Enum):
    """Memory source priority order"""
    REDIS = 1      # Fastest - session memory
    MONGODB = 2    # Structured + conversation history
    NEO4J = 3      # Relationships + entities
    PINECONE = 4   # Semantic similarity


class MemoryType(Enum):
    """Memory type classification for storage routing"""
    SESSION = "session"           # Temporary session data → Redis
    CONVERSATION = "conversation" # Chat history → MongoDB
    PROFILE = "profile"           # User profile data → MongoDB
    PREFERENCE = "preference"     # User preferences → MongoDB
    RELATIONSHIP = "relationship" # Entities & relations → Neo4j
    SEMANTIC = "semantic"         # Meaningful knowledge → Pinecone


class MemoryFetchResult:
    """Result of a memory fetch operation"""
    def __init__(
        self,
        found: bool,
        source: Optional[MemorySource],
        data: Any,
        query_time_ms: float,
        reason: str
    ):
        self.found = found
        self.source = source
        self.data = data
        self.query_time_ms = query_time_ms
        self.reason = reason


class MemoryStorageResult:
    """Result of a memory storage operation"""
    def __init__(
        self,
        success: bool,
        destination: MemorySource,
        memory_type: MemoryType,
        reason: str,
        data_stored: Any = None
    ):
        self.success = success
        self.destination = destination
        self.memory_type = memory_type
        self.reason = reason
        self.data_stored = data_stored


class UnifiedMemoryOrchestrator:
    """
    🎯 SINGLE SOURCE OF TRUTH for all memory operations
    
    Responsibilities:
    - Fetch memory with stop-on-hit logic
    - Enrich master prompt with memory context
    - Route storage to correct memory system
    - Provide comprehensive debug logging
    - Prevent duplicates and stale data
    
    ULTRA-OPTIMIZATIONS:
    - In-memory LRU cache for user profiles (60s TTL)
    - Projection queries to reduce data transfer
    - Fast-path for common intents
    """
    
    def __init__(self):
        """Initialize connections to all memory systems"""
        from app.db.redis_client import redis_client
        from app.db.mongo_client import MongoClient, memory_collection, users_collection, tasks_collection, users_global_collection
        from app.db.neo4j_client import Neo4jClient
        from app.services.memory_manager import index as pinecone_index, get_embedding
        from app.services.user_resolution_service import get_user_resolution_service
        
        self.redis = redis_client
        self.mongo = MongoClient()
        self.neo4j = Neo4jClient()
        self.pinecone = pinecone_index
        self.get_embedding = get_embedding
        self.memory_collection = memory_collection
        self.users_collection = users_collection  # 🆕 For user profile with location
        self.tasks_collection = tasks_collection  # 🆕 For task awareness
        self.users_global_collection = users_global_collection # 🆕 For global stats and history
        
        # 🚀 IN-MEMORY CACHE for user profiles (avoids repeated MongoDB hits)
        self._profile_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl_seconds = 60  # Cache profiles for 60 seconds
        self._cache_max_size = 1000   # Max 1000 profiles in cache
        
        # 🔐 User Resolution Service - ensures ONE EMAIL = ONE USER
        try:
            self.user_resolution = get_user_resolution_service()
            logger.info("🔐 User Resolution Service integrated with Memory Orchestrator")
        except Exception as e:
            logger.warning(f"⚠️ User Resolution Service not available yet: {e}")
            self.user_resolution = None
        
        logger.info("🧠 Unified Memory Orchestrator initialized (ULTRA-OPTIMIZED)")
    
    def _get_cached_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile from cache if valid"""
        if user_id in self._profile_cache:
            data, cached_at = self._profile_cache[user_id]
            age = (datetime.now() - cached_at).total_seconds()
            if age < self._cache_ttl_seconds:
                return data
            else:
                # Expired, remove
                del self._profile_cache[user_id]
        return None
    
    def _set_cached_profile(self, user_id: str, data: Dict):
        """Store user profile in cache"""
        # Evict oldest if cache full
        if len(self._profile_cache) >= self._cache_max_size:
            oldest_key = min(self._profile_cache, key=lambda k: self._profile_cache[k][1])
            del self._profile_cache[oldest_key]
        self._profile_cache[user_id] = (data, datetime.now())
    
    def invalidate_cache(self, user_id: str = None):
        """
        🗑️ Invalidate cache to force fresh data fetch
        
        Args:
            user_id: Specific user to invalidate. If None, clears ALL cache.
        """
        if user_id:
            if user_id in self._profile_cache:
                del self._profile_cache[user_id]
                logger.info(f"🗑️ [Cache] Invalidated cache for user {user_id[:8]}...")
        else:
            self._profile_cache.clear()
            logger.info("🗑️ [Cache] Cleared ALL profile cache")
    
    # ==========================================
    # MEMORY FETCHING (Stop-on-Hit Logic)
    # ==========================================
    
    # ==========================================
    # HOLOGRAPHIC MEMORY RETRIEVAL (ULTRA-OPTIMIZED)
    # ==========================================
    
    async def get_holographic_context(
        self,
        user_id: str = None,              # Support positional for backwards compatibility
        query: str = None,
        intent: str = "general",
        user_id_or_email: str = None      # Also accept named parameter
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        💎 HOLOGRAPHIC MEMORY RETRIEVAL (ULTRA-FAST)
        
        OPTIMIZATIONS:
        - Resolve user ID first
        - Skip heavy fetches for simple intents
        - Only fetch MongoDB profile (fastest, most useful)
        - Neo4j/Pinecone only for "history" or "preferences" intents
        
        Args:
            user_id: User ID (preferred)
            query: The user's query/message
            intent: The detected intent
            user_id_or_email: Alternative parameter name (for backwards compatibility)
        """
        # Handle both parameter styles
        actual_user_id = user_id or user_id_or_email
        if not actual_user_id:
            raise ValueError("user_id or user_id_or_email is required")
        
        debug_logs = []
        start_time = datetime.now()
        
        # 0. Resolve User Identity
        resolved_user_id, is_new, resolve_logs = await self.validate_and_resolve_user_id(actual_user_id)
        debug_logs.extend(resolve_logs)
        
        debug_logs.append(f"[Holographic Fetch START] user_id={resolved_user_id}, intent={intent}")
        
        # 🚀 ULTRA-FAST: Skip heavy fetches for simple intents
        # "identity" and "preferences" need MongoDB profile (fastest) - NOT full Neo4j/Pinecone search
        fast_intents = ["general", "greeting", "thanks", "media", "task", "coding"]
        
        # 🆕 "identity" and "preferences" intents ONLY need MongoDB (where name/age/profile/preferences are stored)
        # Neo4j/Pinecone are TOO SLOW and cause timeouts - user profile and preferences are in MongoDB!
        if intent in ["identity", "preferences"]:
            debug_logs.append(f"🔍 [IDENTITY INTENT] Fast MongoDB-only fetch for user profile")
            # ONLY fetch MongoDB profile - this is where name/email/location lives
            mongo_result = await self._fetch_from_mongodb(resolved_user_id, query, intent)
            
            context = {
                "session": {},
                "global_stats": {},
                "profile": mongo_result.data if mongo_result.found else {},
                "relationships": [],
                "memories": [],
                "tasks": []
            }
            
            if mongo_result.found:
                debug_logs.append(f"✅ MongoDB: Found profile (name={mongo_result.data.get('name')}) ({mongo_result.query_time_ms:.1f}ms)")
            else:
                debug_logs.append(f"⚠️ MongoDB: No profile found ({mongo_result.query_time_ms:.1f}ms)")
            
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            debug_logs.append(f"[Holographic Fetch END - {intent.upper()} FAST PATH] Total time: {total_time:.1f}ms")
            return context, debug_logs
            
        elif intent in fast_intents:
            debug_logs.append(f"⚡ [ULTRA-FAST] Skipping heavy fetches for intent: {intent}")
            # Only fetch MongoDB profile (usually <10ms)
            mongo_result = await self._fetch_from_mongodb(resolved_user_id, query, intent)
            
            context = {
                "session": {},
                "global_stats": {},
                "profile": mongo_result.data if mongo_result.found else {},
                "relationships": [],
                "memories": [],
                "tasks": []
            }
            
            # 🚀 ALSO fetch tasks for "task" intent
            if intent == "task":
                 task_res = await self._fetch_from_tasks(resolved_user_id)
                 if task_res.found:
                     context["tasks"] = task_res.data
                     debug_logs.append(f"✅ Tasks: Found {len(context['tasks'])} recent tasks ({task_res.query_time_ms:.1f}ms)")
            
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            debug_logs.append(f"[Holographic Fetch END - FAST PATH] Total time: {total_time:.1f}ms")
            return context, debug_logs
        
        # Full fetch only for "history" or "preferences" intents
        debug_logs.append(f"📚 [FULL FETCH] Deep memory search for intent: {intent}")
        
        # Launch parallel tasks
        redis_task = self._fetch_from_redis(resolved_user_id, query)
        global_task = self._fetch_global_stats(resolved_user_id) # 🆕 Fetch global stats
        mongo_task = self._fetch_from_mongodb(resolved_user_id, query, intent)
        neo4j_task = self._fetch_from_neo4j(resolved_user_id, query)
        pinecone_task = self._fetch_from_pinecone(resolved_user_id, query)
        task_task = self._fetch_from_tasks(resolved_user_id)  # Always fetch recent tasks for context
        
        # Wait for all results (gather)
        results = await asyncio.gather(
            redis_task, 
            global_task,
            mongo_task, 
            neo4j_task, 
            pinecone_task, 
            task_task,
            return_exceptions=True
        )
        
        redis_res, global_res, mongo_res, neo4j_res, pinecone_res, task_res = results
        
        # Process results & build context
        context = {
            "session": {},
            "global_stats": {},
            "profile": {},
            "relationships": [],
            "memories": [],
            "tasks": []
        }
        
        # 1. Redis (Session)
        if isinstance(redis_res, MemoryFetchResult) and redis_res.found:
            context["session"] = redis_res.data
            debug_logs.append(f"✅ Redis: Found session context ({redis_res.query_time_ms:.1f}ms)")
        elif isinstance(redis_res, Exception):
            debug_logs.append(f"❌ Redis Error: {str(redis_res)}")

        # 1.5 Global Stats
        if isinstance(global_res, MemoryFetchResult) and global_res.found:
            context["global_stats"] = global_res.data
            debug_logs.append(f"✅ Global: Found user stats ({global_res.query_time_ms:.1f}ms)")
            
        # 2. MongoDB (Profile)
        if isinstance(mongo_res, MemoryFetchResult) and mongo_res.found:
            context["profile"] = mongo_res.data
            debug_logs.append(f"✅ MongoDB: Found profile data ({mongo_res.query_time_ms:.1f}ms)")
        elif isinstance(mongo_res, Exception):
            debug_logs.append(f"❌ MongoDB Error: {str(mongo_res)}")
            
        # 3. Neo4j (Graph)
        if isinstance(neo4j_res, MemoryFetchResult) and neo4j_res.found:
            context["relationships"] = neo4j_res.data.get("relationships", [])
            debug_logs.append(f"✅ Neo4j: Found {len(context['relationships'])} relationships ({neo4j_res.query_time_ms:.1f}ms)")
        elif isinstance(neo4j_res, Exception):
            debug_logs.append(f"❌ Neo4j Error: {str(neo4j_res)}")
            
        # 4. Pinecone (Vector)
        if isinstance(pinecone_res, MemoryFetchResult) and pinecone_res.found:
            context["memories"] = pinecone_res.data.get("memories", [])
            debug_logs.append(f"✅ Pinecone: Found {len(context['memories'])} semantic memories ({pinecone_res.query_time_ms:.1f}ms)")
        elif isinstance(pinecone_res, Exception):
            debug_logs.append(f"❌ Pinecone Error: {str(pinecone_res)}")
            
        # 5. Tasks (MongoDB)
        if isinstance(task_res, MemoryFetchResult) and task_res.found:
            context["tasks"] = task_res.data
            debug_logs.append(f"✅ Tasks: Found {len(context['tasks'])} recent tasks ({task_res.query_time_ms:.1f}ms)")
        elif isinstance(task_res, Exception):
            debug_logs.append(f"❌ Task Error: {str(task_res)}")
            
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        debug_logs.append(f"[Holographic Fetch END] Total time: {total_time:.1f}ms")
        
        return context, debug_logs
    
    async def _empty_fetch(self, source: MemorySource) -> MemoryFetchResult:
        """Helper for skipping fetches"""
        return MemoryFetchResult(
            found=False,
            source=source,
            data=None,
            query_time_ms=0,
            reason="Skipped optimization"
        )

    async def _fetch_global_stats(self, user_id: str) -> MemoryFetchResult:
        """Fetch global user statistics (conversation count, first interaction, etc.)"""
        start = datetime.now()
        
        try:
            # Try to get stats from users_global_collection if available
            if self.users_global_collection is not None:
                from bson import ObjectId
                user_obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
                
                if user_obj_id:
                    global_data = await self.users_global_collection.find_one(
                        {"user_id": user_id},  # Global stats keyed by user_id string
                        {"_id": 0, "conversation_count": 1, "first_interaction": 1, "last_interaction": 1}
                    )
                    
                    query_time = (datetime.now() - start).total_seconds() * 1000
                    
                    if global_data:
                        return MemoryFetchResult(
                            found=True,
                            source=MemorySource.MONGODB,
                            data=global_data,
                            query_time_ms=query_time,
                            reason=f"Found global stats for user {user_id[:8]}..."
                        )
            
            query_time = (datetime.now() - start).total_seconds() * 1000
            return MemoryFetchResult(
                found=False,
                source=MemorySource.MONGODB,
                data=None,
                query_time_ms=query_time,
                reason="No global stats found"
            )
        except Exception as e:
            query_time = (datetime.now() - start).total_seconds() * 1000
            logger.warning(f"Global stats fetch failed: {e}")
            return MemoryFetchResult(
                found=False,
                source=MemorySource.MONGODB,
                data=None,
                query_time_ms=query_time,
                reason=f"Error: {str(e)}"
            )

    async def _fetch_from_redis(self, user_id: str, query: str) -> MemoryFetchResult:
        """Fetch from Redis (session memory)"""
        start = datetime.now()
        
        try:
            # Check for session-specific data
            session_key = f"session:{user_id}:context"
            cached_data = await self.redis.get(session_key)
            
            query_time = (datetime.now() - start).total_seconds() * 1000
            
            if cached_data:
                import json
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                return MemoryFetchResult(
                    found=True,
                    source=MemorySource.REDIS,
                    data=data,
                    query_time_ms=query_time,
                    reason=f"Found session context for user {user_id}"
                )
            
            return MemoryFetchResult(
                found=False,
                source=MemorySource.REDIS,
                data=None,
                query_time_ms=query_time,
                reason="No session context found in Redis"
            )
        except Exception as e:
            query_time = (datetime.now() - start).total_seconds() * 1000
            logger.warning(f"Redis fetch failed: {e}")
            return MemoryFetchResult(
                found=False,
                source=MemorySource.REDIS,
                data=None,
                query_time_ms=query_time,
                reason=f"Redis error: {str(e)}"
            )
    
    async def _fetch_from_mongodb(
        self,
        user_id: str,
        query: str,
        intent: str
    ) -> MemoryFetchResult:
        """Fetch from MongoDB (structured memory + user profile) - ULTRA-OPTIMIZED with CACHE"""
        start = datetime.now()
        
        try:
            # 🚀 CHECK CACHE FIRST (0ms if hit!)
            cached = self._get_cached_profile(user_id)
            if cached is not None and cached:  # Only use cache if it has actual data
                query_time = (datetime.now() - start).total_seconds() * 1000
                logger.info(f"⚡ [CACHE HIT] Profile for {user_id[:8]}...: name={cached.get('name')} ({query_time:.1f}ms)")
                
                return MemoryFetchResult(
                    found=True,
                    source=MemorySource.MONGODB,
                    data=cached,
                    query_time_ms=query_time,
                    reason=f"Cache hit for user {user_id[:8]}..."
                )
            
            # 🆕 Don't use cached empty results - always check DB for potentially new data
            logger.info(f"🔍 [MongoDB] Fetching profile for user {user_id[:8]}... (cache miss or empty)")
            
            # 🆕 FETCH FROM users_collection FIRST (has location, name, etc.)
            from bson import ObjectId
            user_obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
            
            if not user_obj_id:
                logger.warning(f"⚠️ [MongoDB] Invalid user_id format: {user_id[:8]}... - cannot convert to ObjectId")
            
            user_profile = None
            if user_obj_id:
                try:
                    user_profile = await self.users_collection.find_one(
                        {"_id": user_obj_id},
                        {
                            "_id": 0,
                            "name": 1,
                            "email": 1,
                            "age": 1,           # 🆕 Add age
                            "occupation": 1,    # 🆕 Add occupation
                            "interests": 1,
                            "hobbies": 1,
                            "profile": 1,  # Contains location, city, state, country
                            "responseStyle": 1,
                            "nickname": 1       # 🆕 Add nickname
                        }
                    )
                    if user_profile:
                        logger.info(f"✅ [MongoDB] Found user profile: name={user_profile.get('name')}, age={user_profile.get('age')}")
                    else:
                        logger.warning(f"⚠️ [MongoDB] No profile document found for user {user_id[:8]}...")
                except Exception as e:
                    logger.error(f"❌ [MongoDB] Error fetching user profile: {e}")
            
            # 🚀 ALSO check memory_collection for structured memories
            user_memory = await self.memory_collection.find_one(
                {"userId": user_id},
                {
                    "_id": 0,  # Exclude _id
                    "name": 1,
                    "interests": 1,
                    "preferences": 1,
                    "profile": 1
                }
            )
            
            # 🧠 ALSO check semantic_memories collection for stored facts/preferences
            semantic_memories = await self.db["semantic_memories"].find(
                {"user_id": user_id, "type": {"$in": ["preference", "fact", "identity"]}},
                {"_id": 0, "content": 1, "type": 1, "value": 1}
            ).sort("created_at", -1).limit(20).to_list(length=20)
            
            query_time = (datetime.now() - start).total_seconds() * 1000
            
            # 🧠 MERGE DATA from both collections
            memory_data = {
                "name": None,
                "nickname": None,
                "email": None,
                "age": None,
                "occupation": None,
                "interests": [],
                "hobbies": [],
                "preferences": [],
                "profile": {},
                "location": None,
                "city": None,
                "state": None,
                "country": None,
                "responseStyle": None
            }
            
            # Priority: user_profile > user_memory
            if user_profile:
                memory_data["name"] = user_profile.get("name")
                memory_data["nickname"] = user_profile.get("nickname")
                memory_data["email"] = user_profile.get("email")
                memory_data["age"] = user_profile.get("age")
                memory_data["occupation"] = user_profile.get("occupation")
                memory_data["interests"] = user_profile.get("interests", [])[:5]
                memory_data["hobbies"] = user_profile.get("hobbies", [])[:5]
                memory_data["responseStyle"] = user_profile.get("responseStyle")
                
                # 🌍 EXTRACT LOCATION from profile
                profile = user_profile.get("profile", {})
                if isinstance(profile, dict):
                    memory_data["profile"] = profile
                    memory_data["location"] = profile.get("location")
                    memory_data["city"] = profile.get("city")
                    memory_data["state"] = profile.get("state")
                    memory_data["country"] = profile.get("country")
                    
                    # Log location discovery
                    if memory_data["location"] or memory_data["city"]:
                        logger.info(f"🌍 [MongoDB] Found location: {memory_data.get('city') or memory_data.get('location')}")
            
            # Merge from memory_collection if user_profile missing data
            if user_memory:
                if not memory_data["name"]:
                    memory_data["name"] = user_memory.get("name")
                if not memory_data["interests"]:
                    memory_data["interests"] = user_memory.get("interests", [])[:5]
                memory_data["preferences"] = user_memory.get("preferences", [])[:5]
            
            # 🧠 Merge semantic memories (recent facts/preferences)
            if semantic_memories:
                logger.info(f"🧠 [MongoDB] Found {len(semantic_memories)} semantic memories")
                for mem in semantic_memories:
                    mem_value = mem.get("value") or mem.get("content")
                    if mem_value and mem_value not in memory_data["preferences"]:
                        memory_data["preferences"].append(mem_value)
                # Limit to 10 total
                memory_data["preferences"] = memory_data["preferences"][:10]
                
                # Check for location in memory_collection too
                mem_profile = user_memory.get("profile", {})
                if isinstance(mem_profile, dict):
                    if not memory_data["location"]:
                        memory_data["location"] = mem_profile.get("location")
                    if not memory_data["city"]:
                        memory_data["city"] = mem_profile.get("city")
            
            # Check if any relevant data exists
            has_data = (
                memory_data["name"] or
                memory_data["age"] or
                memory_data["occupation"] or
                memory_data["nickname"] or
                len(memory_data["interests"]) > 0 or
                len(memory_data["preferences"]) > 0 or
                len(memory_data["profile"]) > 0 or
                memory_data["location"] or
                memory_data["city"]
            )
            
            if has_data:
                # 🧠 LOG IDENTITY DATA FOUND
                identity_parts = []
                if memory_data["name"]: identity_parts.append(f"name={memory_data['name']}")
                if memory_data["age"]: identity_parts.append(f"age={memory_data['age']}")
                if memory_data["occupation"]: identity_parts.append(f"occupation={memory_data['occupation']}")
                if memory_data["location"]: identity_parts.append(f"location={memory_data['location']}")
                if identity_parts:
                    logger.info(f"🧠 [Identity Recall] {', '.join(identity_parts)} for user {user_id[:8]}...")
                
                # 🚀 CACHE the result for next time
                self._set_cached_profile(user_id, memory_data)
                
                return MemoryFetchResult(
                    found=True,
                    source=MemorySource.MONGODB,
                    data=memory_data,
                    query_time_ms=query_time,
                    reason=f"Found user profile + memory for user {user_id[:8]}..."
                )
            
            # 🚀 CACHE empty result too (avoid repeated empty lookups)
            self._set_cached_profile(user_id, {})
            
            return MemoryFetchResult(
                found=False,
                source=MemorySource.MONGODB,
                data=None,
                query_time_ms=query_time,
                reason="No user profile or memory found in MongoDB"
            )
        except Exception as e:
            query_time = (datetime.now() - start).total_seconds() * 1000
            logger.warning(f"MongoDB fetch failed: {e}")
            return MemoryFetchResult(
                found=False,
                source=MemorySource.MONGODB,
                data=None,
                query_time_ms=query_time,
                reason=f"MongoDB error: {str(e)}"
            )

            
    async def _fetch_from_tasks(self, user_id: str) -> MemoryFetchResult:
        """Fetch recent tasks from MongoDB"""
        start = datetime.now()
        try:
            # Fetch last 5 active/pending tasks + 3 recently completed
            # Sort by updated_at desc
            tasks = await self.tasks_collection.find(
                {"userId": user_id},
                {"_id": 0, "title": 1, "status": 1, "priority": 1, "dueDate": 1}
            ).sort("updated_at", -1).limit(5).to_list(length=5)
            
            query_time = (datetime.now() - start).total_seconds() * 1000
            
            if tasks:
                return MemoryFetchResult(
                    found=True,
                    source=MemorySource.MONGODB,
                    data=tasks,
                    query_time_ms=query_time,
                    reason=f"Found {len(tasks)} recent tasks"
                )
            
            return MemoryFetchResult(
                found=False,
                source=MemorySource.MONGODB,
                data=None,
                query_time_ms=query_time,
                reason="No recent tasks found"
            )
        except Exception as e:
            query_time = (datetime.now() - start).total_seconds() * 1000
            return MemoryFetchResult(
                found=False,
                source=MemorySource.MONGODB,
                data=None,
                query_time_ms=query_time,
                reason=f"Task fetch failed: {str(e)}"
            )
    async def _fetch_from_neo4j(self, user_id: str, query: str) -> MemoryFetchResult:
        """
        Fetch from Neo4j (relationships + entities)
        🧠 STRONG FEATURE: Recursive Retrieval (Graph Reasoning)
        """
        start = datetime.now()
        
        try:
            if not self.neo4j.is_available:
                query_time = (datetime.now() - start).total_seconds() * 1000
                return MemoryFetchResult(
                    found=False,
                    source=MemorySource.NEO4J,
                    data=None,
                    query_time_ms=query_time,
                    reason="Neo4j not available"
                )
            
            # Query Neo4j for user's relationships AND related concepts (2-hop)
            async with self.neo4j._driver.session() as session:
                result = await session.run(
                    """
                    MATCH (u:User {id: $user_id})-[r1]->(n)
                    OPTIONAL MATCH (n)-[r2]->(related)
                    WHERE NOT (u)-->(related) AND related IS NOT NULL
                    RETURN 
                        type(r1) as direct_rel, 
                        n.name as direct_target, 
                        coalesce(n.value, "") as value,
                        type(r2) as indirect_rel,
                        related.name as indirect_target,
                        labels(n) as direct_labels
                    ORDER BY r1.created_at DESC
                    LIMIT 15
                    """,
                    user_id=user_id
                )
                
                records = await result.data()
                query_time = (datetime.now() - start).total_seconds() * 1000
                
                if records:
                    relationships = []
                    seen_targets = set()
                    
                    for record in records:
                        # Add direct relationship
                        if record["direct_target"] not in seen_targets:
                            relationships.append({
                                "type": record["direct_rel"],
                                "target": record["direct_target"],
                                "value": record.get("value"),
                                "depth": 1
                            })
                            seen_targets.add(record["direct_target"])
                        
                        # Add indirect relationship (Graph Reasoning)
                        if record["indirect_target"] and record["indirect_target"] not in seen_targets:
                            relationships.append({
                                "type": "RELATED_VIA_" + record["direct_target"],
                                "target": record["indirect_target"],
                                "depth": 2,
                                "reasoning": f"Because you like {record['direct_target']}"
                            })
                            seen_targets.add(record["indirect_target"])
                    
                    return MemoryFetchResult(
                        found=True,
                        source=MemorySource.NEO4J,
                        data={"relationships": relationships},
                        query_time_ms=query_time,
                        reason=f"Found {len(relationships)} relationships (including inferred ones)"
                    )
                
                return MemoryFetchResult(
                    found=False,
                    source=MemorySource.NEO4J,
                    data=None,
                    query_time_ms=query_time,
                    reason="No relationships found in Neo4j"
                )
        except Exception as e:
            query_time = (datetime.now() - start).total_seconds() * 1000
            logger.warning(f"Neo4j fetch failed: {e}")
            return MemoryFetchResult(
                found=False,
                source=MemorySource.NEO4J,
                data=None,
                query_time_ms=query_time,
                reason=f"Neo4j error: {str(e)}"
            )
    
    async def _fetch_from_pinecone(self, user_id: str, query: str) -> MemoryFetchResult:
        """Fetch from Pinecone (semantic similarity)"""
        start = datetime.now()
        
        try:
            if not self.pinecone:
                query_time = (datetime.now() - start).total_seconds() * 1000
                return MemoryFetchResult(
                    found=False,
                    source=MemorySource.PINECONE,
                    data=None,
                    query_time_ms=query_time,
                    reason="Pinecone not available"
                )
            
            # Generate embedding for query
            vector = await self.get_embedding(query)
            
            # Query Pinecone
            results = self.pinecone.query(
                vector=vector,
                top_k=3,
                include_metadata=True,
                filter={"user_id": user_id}
            )
            
            query_time = (datetime.now() - start).total_seconds() * 1000
            
            if results and hasattr(results, "matches") and len(results.matches) > 0:
                # 🧠 MEMORY HARDENING PROTOCOL - Fix 3: Score Filtering (>0.75)
                # QUALITY CONTROL: Only accept memories with > 75% match confidence
                memories = [
                    {
                        "text": match.metadata.get("text"),
                        "type": match.metadata.get("type"),
                        "score": match.score
                    }
                    for match in results.matches
                    if match.score > 0.75  # Increased threshold for better quality
                ]
                
                if memories:
                    return MemoryFetchResult(
                        found=True,
                        source=MemorySource.PINECONE,
                        data={"memories": memories},
                        query_time_ms=query_time,
                        reason=f"Found {len(memories)} relevant memories in Pinecone"
                    )
            
            return MemoryFetchResult(
                found=False,
                source=MemorySource.PINECONE,
                data=None,
                query_time_ms=query_time,
                reason="No relevant semantic memories found in Pinecone"
            )
        except Exception as e:
            query_time = (datetime.now() - start).total_seconds() * 1000
            logger.warning(f"Pinecone fetch failed: {e}")
            return MemoryFetchResult(
                found=False,
                source=MemorySource.PINECONE,
                data=None,
                query_time_ms=query_time,
                reason=f"Pinecone error: {str(e)}"
            )
    
    # ==========================================
    # MASTER PROMPT ENRICHMENT
    # ==========================================
    
    # ==========================================
    # MASTER PROMPT ENRICHMENT
    # ==========================================
    
    def enrich_master_prompt(
        self,
        base_prompt: str,
        context: Dict[str, Any],
        debug_logs: List[str]
    ) -> Tuple[str, List[str]]:
        """
        🎯 ENRICH MASTER PROMPT WITH HOLOGRAPHIC CONTEXT
        
        Rules:
        - Inject context from ALL sources
        - Label clearly as [SYSTEM MEMORY CONTEXT]
        - Prioritize: Profile > Location > Relationships > Memories > Session
        - 🆕 NEVER ASK for data that's already available
        """
        debug_logs.append("[Master Prompt] Starting enrichment")
        
        if not any(context.values()):
            debug_logs.append("[Master Prompt] No context to inject - using base prompt")
            return base_prompt, debug_logs
        
        # Build memory context section
        memory_block = "[SYSTEM MEMORY CONTEXT - USE THIS DATA, DON'T ASK FOR IT]\n"
        
        # 🌍 1. LOCATION FIRST (Most commonly needed, most commonly asked redundantly)
        if context.get("profile"):
            profile = context["profile"]
            location_str = None
            
            # Extract location from various fields
            city = profile.get("city")
            location = profile.get("location")
            state = profile.get("state")
            country = profile.get("country")
            
            # Also check nested profile object
            nested_profile = profile.get("profile", {})
            if isinstance(nested_profile, dict):
                city = city or nested_profile.get("city")
                location = location or nested_profile.get("location")
                state = state or nested_profile.get("state")
                country = country or nested_profile.get("country")
            
            if city or location:
                parts = [p for p in [city, state, country] if p]
                location_str = ", ".join(parts) if parts else location
                memory_block += f"🌍 USER LOCATION: {location_str}\n"
                memory_block += f"   ⚠️ USE THIS FOR 'near me', 'around here', 'nearby' queries!\n"
                memory_block += f"   ⚠️ DO NOT ASK user for location - you already have it!\n\n"
                logger.info(f"🌍 [Prompt] Injected location: {location_str}")
        
        # 1.5 Global Context (Project Awareness)
        if context.get("global_stats"):
            stats = context["global_stats"]
            memory_block += "📊 GLOBAL USER CONTEXT:\n"
            if stats.get("total_sessions"):
                memory_block += f"  - Total Collaboration Sessions: {stats['total_sessions']}\n"
            if stats.get("joined_at"):
                memory_block += f"  - User Since: {stats['joined_at']}\n"
            memory_block += "\n"

        # 2. User Profile (MongoDB)
        if context.get("profile"):
            profile = context["profile"]
            memory_block += "👤 USER PROFILE (verified data - USE IT, don't ask):\n"
            if profile.get("name"):
                memory_block += f"  - Name: {profile['name']}\n"
                # 🔥 CRITICAL: Add explicit instruction for identity queries
                memory_block += f"  ⚠️ WHEN ASKED 'what is my name?' → RESPOND: 'Your name is {profile['name']}'\n"
                logger.info(f"✅ [Prompt Enrichment] Added name to prompt: {profile['name']}")
            if profile.get("nickname"):
                memory_block += f"  - Nickname: {profile['nickname']}\n"
            if profile.get("email"):
                memory_block += f"  - Email: {profile['email']}\n"
            if profile.get("age"):
                memory_block += f"  - Age: {profile['age']}\n"
            if profile.get("occupation"):
                memory_block += f"  - Occupation: {profile['occupation']}\n"
            if profile.get("interests"):
                interests = profile['interests']
                if isinstance(interests, list):
                    memory_block += f"  - Interests: {', '.join(interests[:5])}\n"
            if profile.get("hobbies"):
                hobbies = profile['hobbies']
                if isinstance(hobbies, list):
                    memory_block += f"  - Hobbies: {', '.join(hobbies[:5])}\n"
            
            # 🎨 PREFERENCES (Colors, likes, dislikes) - CRITICAL FOR RECALL
            if profile.get("preferences"):
                prefs = profile['preferences']
                if isinstance(prefs, list) and prefs:
                    memory_block += f"\n🎨 USER PREFERENCES:\n"
                    for pref in prefs[:10]:
                        memory_block += f"  - {pref}\n"
                    memory_block += f"   ⚠️ WHEN ASKED 'what do I like', 'my favorite', 'which color' → USE THESE!\n"
                    memory_block += f"   ⚠️ DO NOT ASK - you already know their preferences!\n\n"
                    logger.info(f"🎨 [Prompt] Injected {len(prefs[:10])} preferences")
            
            if profile.get("responseStyle"):
                memory_block += f"  - Preferred Style: {profile['responseStyle']}\n"
            memory_block += "\n"
            
        # 3. Relationships (Neo4j)
        if context.get("relationships"):
            memory_block += "🕸️ Knowledge Graph:\n"
            for rel in context["relationships"]:
                if rel.get("reasoning"):
                     memory_block += f"  - {rel['type']} → {rel['target']} ({rel['reasoning']})\n"
                else:
                     memory_block += f"  - {rel['type']} → {rel['target']}\n"
            memory_block += "\n"
            
        # 4. Semantic Memories (Pinecone)
            
        # 5. Recent Tasks (MongoDB)
        if context.get("tasks"):
            memory_block += "📋 Recent Tasks (Known Context):\n"
            for task in context["tasks"]:
                status_icon = "✅" if task.get("status") == "completed" else "⏳"
                memory_block += f"  - {status_icon} {task.get('title')} [{task.get('status')}]\n"
            memory_block += "\n"
        
        # 6. Semantic Memories (Pinecone)
        if context.get("memories"):
            memory_block += "🧠 Relevant Memories:\n"
            for mem in context["memories"]:
                memory_block += f"  - {mem['text']} (confidence: {mem['score']:.2f})\n"
            memory_block += "\n"
            
        # 5. Session Context (Redis)
        if context.get("session"):
            memory_block += "⚡ Session Context:\n"
            for key, value in context["session"].items():
                if key != "timestamp":
                    memory_block += f"  - {key}: {value}\n"
            memory_block += "\n"
        
        # 🆕 CRITICAL INSTRUCTION
        memory_block += """
⚠️ CRITICAL INTELLIGENCE RULES:
1. If location is available above → USE IT for "near me" queries
2. If name is available above → USE IT, don't ask "what's your name?"
3. NEVER ask for information that's already provided in this context
4. Make CONFIDENT responses using available data
5. For "near me" → respond with: "Here are [results] near you in [location]..."
[END SYSTEM MEMORY CONTEXT]

"""
        
        # Inject memory context into prompt
        enriched_prompt = memory_block + base_prompt
        
        debug_logs.append(f"[Master Prompt] Injected {len(memory_block)} chars of holographic context")
        
        return enriched_prompt, debug_logs
    
    # ==========================================
    # MEMORY STORAGE (Smart Routing)
    # ==========================================
    
    async def store_memory(
        self,
        user_id: str,
        memory_content: Any,
        memory_type: MemoryType,
        metadata: Optional[Dict] = None
    ) -> Tuple[MemoryStorageResult, List[str]]:
        """
        🎯 PRO-LEVEL MEMORY STORAGE (Robust & Verified)
        
        Rules:
        - Multi-system storage (Cross-pollination)
        - Parallel execution for speed
        - Verified database writes
        - Tracks user engagement stats
        """
        debug_logs = []
        start_time = datetime.now()
        
        # 1. Resolve User ID (Email -> ID)
        canonical_user_id, is_new, resolve_logs = await self.validate_and_resolve_user_id(user_id)
        debug_logs.extend(resolve_logs)
        
        debug_logs.append(f"[Memory Storage START] user_id={canonical_user_id}, type={memory_type.value}")
        
        # 2. Validation
        if not memory_content or (isinstance(memory_content, str) and len(memory_content.strip()) < 2):
            debug_logs.append("[Memory Storage SKIP] Content too short or empty")
            return MemoryStorageResult(
                success=False,
                destination=None,
                memory_type=memory_type,
                reason="Content validation failed"
            ), debug_logs

        # 3. Increment Engagement Stats (Background)
        asyncio.create_task(self.update_user_stats(canonical_user_id))
        
        tasks = []
        
        # 4. Routing Logic
        if memory_type == MemoryType.SESSION:
            tasks.append(self._store_to_redis(canonical_user_id, memory_content, metadata, debug_logs))
            
        elif memory_type in [MemoryType.PROFILE, MemoryType.PREFERENCE]:
            tasks.append(self._store_to_mongodb(canonical_user_id, memory_content, memory_type, metadata, debug_logs))
            # Cross-pollinate preference to Semantic
            if memory_type == MemoryType.PREFERENCE:
                tasks.append(self._store_to_pinecone_with_dedup(
                    canonical_user_id, 
                    f"User Preference: {memory_content}", 
                    {"source": "preference_sync"}, 
                    []
                ))
                
        elif memory_type == MemoryType.RELATIONSHIP:
            tasks.append(self._store_to_neo4j(canonical_user_id, memory_content, metadata, debug_logs))
            # Cross-pollinate relationship to Semantic
            if isinstance(memory_content, (list, tuple)):
                rel_type, target = memory_content
                tasks.append(self._store_to_pinecone_with_dedup(
                    canonical_user_id, 
                    f"Relationship: {rel_type} -> {target}",
                    {"source": "relationship_sync"}, 
                    []
                ))
                
        elif memory_type == MemoryType.SEMANTIC:
            tasks.append(self._store_to_pinecone_with_dedup(canonical_user_id, memory_content, metadata, debug_logs))
            
        # Execute all storage tasks in parallel
        if tasks:
            storage_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Find the "primary" result to return (for legacy compatibility)
            main_result = None
            for res in storage_results:
                if isinstance(res, MemoryStorageResult):
                    if not main_result: main_result = res
                    if res.success: main_result = res # Prefer success
                elif isinstance(res, Exception):
                    debug_logs.append(f"❌ Storage task error: {str(res)}")
            
            result = main_result or MemoryStorageResult(False, MemorySource.UNKNOWN, memory_type, "No storage tasks succeeded")
        else:
            result = MemoryStorageResult(False, MemorySource.UNKNOWN, memory_type, "No storage route found")
            
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        debug_logs.append(f"[Memory Storage END] total_time={total_time:.2f}ms, success={result.success}")
        
        return result, debug_logs
    
    async def _store_to_pinecone_with_dedup(
        self,
        user_id: str,
        content: str,
        metadata: Optional[Dict],
        debug_logs: List[str]
    ) -> MemoryStorageResult:
        """
        🧠 SEMANTIC DEDUPLICATION STRATEGY
        1. Convert new memory to vector.
        2. Query Pinecone for similar vectors (> 0.90).
        3. If found -> SKIP (Duplicate).
        4. If not found -> STORE (New).
        """
        try:
            if not self.pinecone:
                return MemoryStorageResult(False, MemorySource.PINECONE, MemoryType.SEMANTIC, "Pinecone unavailable")

            # 1. Vectorize
            vector = await self.get_embedding(content)
            
            # 2. Check for Similarity
            results = self.pinecone.query(
                vector=vector,
                top_k=1,
                include_metadata=True,
                filter={"user_id": user_id}
            )
            
            if results and results.matches:
                top_match = results.matches[0]
                if top_match.score > 0.90:  # 90% Similarity Threshold
                    debug_logs.append(f"[Pinecone Dedup] SKIP: Found existing memory '{top_match.metadata.get('text')}' (Score: {top_match.score:.2f})")
                    return MemoryStorageResult(
                        success=True, # Considered success as we handled it
                        destination=MemorySource.PINECONE,
                        memory_type=MemoryType.SEMANTIC,
                        reason=f"Duplicate memory skipped (Sim: {top_match.score:.2f})"
                    )

            # 3. Store if unique
            return await self._store_to_pinecone(user_id, content, metadata, debug_logs)
            
        except Exception as e:
            logger.error(f"Dedup check failed: {e}")
            # Fallback to normal store if check fails
            return await self._store_to_pinecone(user_id, content, metadata, debug_logs)

    async def _store_to_redis(
        self,
        user_id: str,
        content: Any,
        metadata: Optional[Dict],
        debug_logs: List[str]
    ) -> MemoryStorageResult:
        """Store session memory to Redis"""
        try:
            import json
            
            session_key = f"session:{user_id}:context"
            data_to_store = {
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Store with 1 hour TTL
            await self.redis.setex(
                session_key,
                3600,  # 1 hour
                json.dumps(data_to_store)
            )
            
            debug_logs.append(f"[Redis Store] Stored session memory with 1h TTL")
            debug_logs.append(f"[Redis Store] Key: {session_key}")
            
            return MemoryStorageResult(
                success=True,
                destination=MemorySource.REDIS,
                memory_type=MemoryType.SESSION,
                reason="Successfully stored session memory to Redis",
                data_stored=data_to_store
            )
        except Exception as e:
            debug_logs.append(f"[Redis Store ERROR] {str(e)}")
            logger.error(f"Failed to store to Redis: {e}")
            return MemoryStorageResult(
                success=False,
                destination=MemorySource.REDIS,
                memory_type=MemoryType.SESSION,
                reason=f"Redis storage failed: {str(e)}"
            )
    
    async def _store_to_mongodb(
        self,
        user_id: str,
        content: Any,
        memory_type: MemoryType,
        metadata: Optional[Dict],
        debug_logs: List[str]
    ) -> MemoryStorageResult:
        """Store structured memory to MongoDB"""
        try:
            # Check for duplicates
            existing = await self.memory_collection.find_one({"userId": user_id})
            
            if memory_type == MemoryType.PROFILE:
                # Update profile data
                update_data = content if isinstance(content, dict) else {"value": content}
                update_data["updated_at"] = datetime.now().isoformat()
                
                await self.memory_collection.update_one(
                    {"userId": user_id},
                    {"$set": update_data},
                    upsert=True
                )
                
                debug_logs.append(f"[MongoDB Store] Updated profile data")
                debug_logs.append(f"[MongoDB Store] Fields: {list(update_data.keys())}")
            
            elif memory_type == MemoryType.PREFERENCE:
                # Add to preferences array (avoid duplicates)
                pref_value = content if isinstance(content, str) else str(content)
                
                # Check if preference already exists
                if existing and pref_value in existing.get("preferences", []):
                    debug_logs.append(f"[MongoDB Store SKIP] Preference already exists: {pref_value}")
                    return MemoryStorageResult(
                        success=True,
                        destination=MemorySource.MONGODB,
                        memory_type=memory_type,
                        reason="Duplicate preference - skipped"
                    )
                
                await self.memory_collection.update_one(
                    {"userId": user_id},
                    {
                        "$addToSet": {"preferences": pref_value},
                        "$set": {"updated_at": datetime.now().isoformat()}
                    },
                    upsert=True
                )
                
                debug_logs.append(f"[MongoDB Store] Added preference: {pref_value}")
            
            elif memory_type == MemoryType.CONVERSATION:
                # Store conversation in separate collection (not implemented here)
                debug_logs.append(f"[MongoDB Store] Conversation storage not implemented in this method")
                return MemoryStorageResult(
                    success=False,
                    destination=MemorySource.MONGODB,
                    memory_type=memory_type,
                    reason="Use separate conversation storage method"
                )
            
            return MemoryStorageResult(
                success=True,
                destination=MemorySource.MONGODB,
                memory_type=memory_type,
                reason=f"Successfully stored {memory_type.value} to MongoDB",
                data_stored=content
            )
        except Exception as e:
            debug_logs.append(f"[MongoDB Store ERROR] {str(e)}")
            logger.error(f"Failed to store to MongoDB: {e}")
            return MemoryStorageResult(
                success=False,
                destination=MemorySource.MONGODB,
                memory_type=memory_type,
                reason=f"MongoDB storage failed: {str(e)}"
            )
    
    async def _store_to_neo4j(
        self,
        user_id: str,
        content: Any,
        metadata: Optional[Dict],
        debug_logs: List[str]
    ) -> MemoryStorageResult:
        """Store relationship to Neo4j"""
        try:
            if not self.neo4j.is_available:
                debug_logs.append("[Neo4j Store SKIP] Neo4j not available")
                return MemoryStorageResult(
                    success=False,
                    destination=MemorySource.NEO4J,
                    memory_type=MemoryType.RELATIONSHIP,
                    reason="Neo4j not available"
                )
            
            # Content should be a tuple: (relationship_type, target_value)
            if not isinstance(content, (list, tuple)) or len(content) != 2:
                debug_logs.append(f"[Neo4j Store ERROR] Invalid relationship format: {content}")
                return MemoryStorageResult(
                    success=False,
                    destination=MemorySource.NEO4J,
                    memory_type=MemoryType.RELATIONSHIP,
                    reason="Invalid relationship format - expected (type, target)"
                )
            
            rel_type, target_value = content
            
            # Create relationship in Neo4j
            async with self.neo4j._driver.session() as session:
                await session.run(
                    f"""
                    MERGE (u:User {{id: $user_id}})
                    // Normalization: Use lowercase for matching to prevent "Python" vs "python" duplicates
                    MERGE (t:Entity {{name: toLower($target_value)}})
                    MERGE (u)-[r:{rel_type}]->(t)
                    SET r.created_at = $timestamp
                    """,
                    user_id=user_id,
                    target_value=target_value,
                    timestamp=datetime.now().isoformat()
                )
            
            debug_logs.append(f"[Neo4j Store] Created relationship: {rel_type} → {target_value}")
            
            return MemoryStorageResult(
                success=True,
                destination=MemorySource.NEO4J,
                memory_type=MemoryType.RELATIONSHIP,
                reason=f"Successfully created relationship in Neo4j",
                data_stored={"type": rel_type, "target": target_value}
            )
        except Exception as e:
            debug_logs.append(f"[Neo4j Store ERROR] {str(e)}")
            logger.error(f"Failed to store to Neo4j: {e}")
            return MemoryStorageResult(
                success=False,
                destination=MemorySource.NEO4J,
                memory_type=MemoryType.RELATIONSHIP,
                reason=f"Neo4j storage failed: {str(e)}"
            )

    async def delete_relationship(
        self,
        user_id: str,
        target: str,
        relationship_type: str
    ) -> bool:
        """
        Delete a relationship from Neo4j
        """
        try:
            if not self.neo4j.is_available:
                return False
            
            async with self.neo4j._driver.session() as session:
                await session.run(
                    """
                    MATCH (u:User {id: $user_id})-[r]->(n)
                    WHERE type(r) = $type AND n.name = $target
                    DELETE r
                    """,
                    user_id=user_id,
                    type=relationship_type,
                    target=target
                )
            
            logger.info(f"🗑️ Deleted relationship: {relationship_type} -> {target}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete relationship: {e}")
            return False

    async def get_knowledge_graph(self, user_id: str) -> Dict[str, List[Any]]:
        """
        Get the full knowledge graph for a user (formatted for frontend visualization)
        """
        try:
            if not self.neo4j.is_available:
                return {"nodes": [], "links": []}
            
            async with self.neo4j._driver.session() as session:
                result = await session.run(
                    """
                    MATCH (u:User {id: $user_id})-[r]->(n)
                    RETURN 
                        u.id as source, 
                        type(r) as label, 
                        n.name as target, 
                        labels(n) as target_labels,
                        id(n) as target_id
                    LIMIT 100
                    """,
                    user_id=user_id
                )
                
                records = await result.data()
                
                nodes = []
                links = []
                seen_nodes = set()
                
                # Always add the user node
                nodes.append({"id": user_id, "name": "Me", "group": "user", "val": 20})
                seen_nodes.add(user_id)
                
                for record in records:
                    target_name = record["target"]
                    target_id = f"node_{target_name}" # Simple ID generation
                    
                    if target_id not in seen_nodes:
                        nodes.append({
                            "id": target_id,
                            "name": target_name,
                            "group": record["target_labels"][0] if record["target_labels"] else "Entity",
                            "val": 10
                        })
                        seen_nodes.add(target_id)
                    
                    links.append({
                        "source": user_id,
                        "target": target_id,
                        "label": record["label"]
                    })
                
                return {"nodes": nodes, "links": links}
                
        except Exception as e:
            logger.error(f"Failed to get knowledge graph: {e}")
            return {"nodes": [], "links": []}
    
    async def _store_to_pinecone(
        self,
        user_id: str,
        content: str,
        metadata: Optional[Dict],
        debug_logs: List[str]
    ) -> MemoryStorageResult:
        """Store semantic memory to Pinecone"""
        try:
            if not self.pinecone:
                debug_logs.append("[Pinecone Store SKIP] Pinecone not available")
                return MemoryStorageResult(
                    success=False,
                    destination=MemorySource.PINECONE,
                    memory_type=MemoryType.SEMANTIC,
                    reason="Pinecone not available"
                )
            
            # Generate embedding
            vector = await self.get_embedding(content)
            
            # Create deterministic ID to prevent duplicates
            import hashlib
            memory_id = hashlib.sha1(
                f"{user_id}|{content.strip().lower()}".encode("utf-8")
            ).hexdigest()
            
            # Upsert to Pinecone
            self.pinecone.upsert(
                vectors=[
                    {
                        "id": memory_id,
                        "values": vector,
                        "metadata": {
                            "user_id": user_id,
                            "text": content,
                            "type": metadata.get("type", "semantic") if metadata else "semantic",
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                ]
            )
            
            debug_logs.append(f"[Pinecone Store] Upserted semantic memory")
            debug_logs.append(f"[Pinecone Store] ID: {memory_id}")
            debug_logs.append(f"[Pinecone Store] Content: {content[:100]}...")
            
            return MemoryStorageResult(
                success=True,
                destination=MemorySource.PINECONE,
                memory_type=MemoryType.SEMANTIC,
                reason="Successfully stored semantic memory to Pinecone",
                data_stored={"id": memory_id, "text": content}
            )
        except Exception as e:
            debug_logs.append(f"[Pinecone Store ERROR] {str(e)}")
            logger.error(f"Failed to store to Pinecone: {e}")
            return MemoryStorageResult(
                success=False,
                destination=MemorySource.PINECONE,
                memory_type=MemoryType.SEMANTIC,
                reason=f"Pinecone storage failed: {str(e)}"
            )
    
    # ==========================================
    # COMPLETE PIPELINE
    # ==========================================
    
    async def process_message_with_memory(
        self,
        user_id: str,
        message: str,
        intent: str = "general"
    ) -> Dict[str, Any]:
        """
        🎯 COMPLETE MEMORY PIPELINE
        
        Flow:
        1. User Input
        2. Intent Detection
        3. Memory Required? → YES/NO
        4. Memory Fetch (stop-on-hit)
        5. Master Prompt Enrichment
        6. Model Response (generated externally)
        7. Memory Store Decision
        8. Memory Persisted
        
        Returns: {
            "memory_context": Dict or None,
            "enriched_prompt": str,
            "debug_logs": List[str],
            "fetch_time_ms": float,
            "memory_found": bool
        }
        """
        all_debug_logs = []
        pipeline_start = datetime.now()
        
        all_debug_logs.append("=" * 60)
        all_debug_logs.append("🧠 MEMORY PIPELINE START")
        all_debug_logs.append("=" * 60)
        all_debug_logs.append(f"User ID: {user_id}")
        all_debug_logs.append(f"Message: {message}")
        all_debug_logs.append(f"Intent: {intent}")
        all_debug_logs.append("")
        
        # Step 1: Determine if memory is needed
        needs_memory = self._analyze_memory_need(message, intent)
        all_debug_logs.append(f"[Pipeline] Memory needed: {needs_memory}")
        
        if not needs_memory:
            all_debug_logs.append("[Pipeline] Skipping memory fetch - not required for this intent")
            all_debug_logs.append("=" * 60)
            return {
                "memory_context": None,
                "enriched_prompt": message,
                "debug_logs": all_debug_logs,
                "fetch_time_ms": 0,
                "memory_found": False
            }
        
        # Step 2: Fetch memory (Holographic Retrieval)
        all_debug_logs.append("")
        memory_data, fetch_logs = await self.get_holographic_context(user_id, message, intent)
        all_debug_logs.extend(fetch_logs)
        
        # Step 3: Enrich prompt
        all_debug_logs.append("")
        enriched_prompt, enrich_logs = self.enrich_master_prompt(
            message,
            memory_data,
            []
        )
        all_debug_logs.extend(enrich_logs)
        
        pipeline_time = (datetime.now() - pipeline_start).total_seconds() * 1000
        
        all_debug_logs.append("")
        all_debug_logs.append("=" * 60)
        all_debug_logs.append(f"🧠 MEMORY PIPELINE END (took {pipeline_time:.2f}ms)")
        all_debug_logs.append("=" * 60)
        
        return {
            "memory_context": memory_data,
            "enriched_prompt": enriched_prompt,
            "debug_logs": all_debug_logs,
            "fetch_time_ms": pipeline_time,
            "memory_found": memory_data is not None
        }
    
    def _analyze_memory_need(self, message: str, intent: str) -> bool:
        """
        Analyze if memory is needed for this message
        
        Some messages don't need memory:
        - Simple greetings
        - General knowledge questions
        - Math calculations
        """
        lower_msg = message.lower()
        
        # Skip memory for simple cases
        simple_patterns = [
            "hello", "hi ", "hey ", "what is", "calculate", "what's",
            "how to", "explain", "define"
        ]
        
        # Always need memory for personal queries
        personal_patterns = [
            "my ", "i am", "i'm ", "remember", "you know",
            "my name", "who am i", "what do i", "do you know me",
            "which ", "what game", "what do i like", "what do i love",
            "where was i", "what did we", "tell me about my", "our ",
            "husband", "wife", "son", "daughter", "friend", "colleague"
        ]
        
        # Check personal first (higher priority)
        for pattern in personal_patterns:
            if pattern in lower_msg:
                return True
        
        # Check simple patterns
        for pattern in simple_patterns:
            if lower_msg.startswith(pattern):
                return False
        
        # Default: use memory for rich conversations
        return True
    
    async def get_user_preferences(self, user_id: str) -> List[str]:
        """
        Helper method to get all user preferences from MongoDB
        
        Returns:
            List of preference strings
        """
        try:
            user_memory = await self.memory_collection.find_one({"userId": user_id})
            if user_memory and "preferences" in user_memory:
                return user_memory["preferences"]
            return []
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return []
    
    async def validate_and_resolve_user_id(self, user_id_or_email: str) -> Tuple[str, bool, List[str]]:
        """
        🔐 VALIDATE AND RESOLVE USER IDENTITY
        
        This method ensures:
        1. Email gets normalized and resolved to canonical user_id
        2. user_id is validated and confirmed to exist
        3. Duplicate users are prevented
        
        Args:
            user_id_or_email: Either user_id (starts with 'u_') or email address
            
        Returns:
            Tuple of:
            - canonical_user_id (str): The validated/resolved user_id
            - is_new_user (bool): True if new user was created
            - debug_logs (List[str]): Resolution logs
            
        Usage:
            user_id, is_new, logs = await orchestrator.validate_and_resolve_user_id("user@gmail.com")
            # Now use user_id for all memory operations
        """
        debug_logs = []
        
        # Check if user resolution service is available
        if not self.user_resolution:
            debug_logs.append("[User Resolution] Service not available - using provided ID as-is")
            return user_id_or_email, False, debug_logs
        
        try:
            # If input looks like user_id (starts with 'u_'), validate it exists
            if user_id_or_email.startswith('u_'):
                debug_logs.append(f"[User Resolution] Input appears to be user_id: {user_id_or_email}")
                
                # Validate user exists
                user_data = await self.user_resolution.get_user_by_id(user_id_or_email)
                if user_data:
                    debug_logs.append(f"[User Resolution] ✅ User ID validated: {user_id_or_email}")
                    return user_id_or_email, False, debug_logs
                else:
                    debug_logs.append(f"[User Resolution] ⚠️ User ID not found: {user_id_or_email}")
                    return user_id_or_email, False, debug_logs
            
            # Otherwise, treat as email and resolve
            else:
                debug_logs.append(f"[User Resolution] Input appears to be email: {user_id_or_email}")
                
                # Resolve email to canonical user_id
                canonical_user_id, is_new, user_data = await self.user_resolution.resolve_user(user_id_or_email)
                
                if is_new:
                    debug_logs.append(f"[User Resolution] ✅ NEW user created: {canonical_user_id}")
                else:
                    debug_logs.append(f"[User Resolution] ✅ EXISTING user resolved: {canonical_user_id}")
                
                debug_logs.append(f"[User Resolution] Email '{user_id_or_email}' → user_id '{canonical_user_id}'")
                
                return canonical_user_id, is_new, debug_logs
        
        except Exception as e:
            debug_logs.append(f"[User Resolution] ❌ Error: {e}")
            logger.error(f"User resolution error: {e}")
            # Fallback: use provided value
            return user_id_or_email, False, debug_logs

    async def update_user_stats(self, user_id: str, messages: int = 1, sessions: int = 0):
        """
        📈 UPDATE GLOBAL USER STATISTICS
        
        Tracks engagement levels across the platform.
        """
        try:
            await self.users_global_collection.update_one(
                {"userId": user_id},
                {
                    "$inc": {
                        "total_messages": messages, 
                        "total_sessions": sessions
                    },
                    "$set": {
                        "last_active": datetime.now()
                    },
                    "$setOnInsert": {
                        "created_at": datetime.now()
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to update user stats for {user_id}: {e}")


# Global singleton instance
unified_memory_orchestrator = UnifiedMemoryOrchestrator()
