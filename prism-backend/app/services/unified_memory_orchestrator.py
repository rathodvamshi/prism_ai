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
    """
    
    def __init__(self):
        """Initialize connections to all memory systems"""
        from app.db.redis_client import redis_client
        from app.db.mongo_client import MongoClient, memory_collection
        from app.db.neo4j_client import Neo4jClient
        from app.services.memory_manager import index as pinecone_index, get_embedding
        from app.services.user_resolution_service import get_user_resolution_service
        
        self.redis = redis_client
        self.mongo = MongoClient()
        self.neo4j = Neo4jClient()
        self.pinecone = pinecone_index
        self.get_embedding = get_embedding
        self.memory_collection = memory_collection
        
        # 🔐 User Resolution Service - ensures ONE EMAIL = ONE USER
        try:
            self.user_resolution = get_user_resolution_service()
            logger.info("🔐 User Resolution Service integrated with Memory Orchestrator")
        except Exception as e:
            logger.warning(f"⚠️ User Resolution Service not available yet: {e}")
            self.user_resolution = None
        
        logger.info("🧠 Unified Memory Orchestrator initialized")
    
    # ==========================================
    # MEMORY FETCHING (Stop-on-Hit Logic)
    # ==========================================
    
    # ==========================================
    # HOLOGRAPHIC MEMORY RETRIEVAL (Gather-All Logic)
    # ==========================================
    
    async def get_holographic_context(
        self,
        user_id: str,
        query: str,
        intent: str = "general"
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        💎 HOLOGRAPHIC MEMORY RETRIEVAL
        
        Fetches context from ALL layers in parallel:
        1. Redis (Session) - Immediate context
        2. MongoDB (Profile) - Core identity
        3. Neo4j (Graph) - Deep relationships
        4. Pinecone (Vector) - Semantic history
        
        Returns:
            (context_dict, debug_logs)
        """
        debug_logs = []
        start_time = datetime.now()
        
        debug_logs.append(f"[Holographic Fetch START] user_id={user_id}, intent={intent}")
        
        # Launch parallel tasks
        redis_task = self._fetch_from_redis(user_id, query)
        mongo_task = self._fetch_from_mongodb(user_id, query, intent)
        neo4j_task = self._fetch_from_neo4j(user_id, query)
        pinecone_task = self._fetch_from_pinecone(user_id, query)
        
        # Wait for all results (gather)
        results = await asyncio.gather(
            redis_task, 
            mongo_task, 
            neo4j_task, 
            pinecone_task, 
            return_exceptions=True
        )
        
        redis_res, mongo_res, neo4j_res, pinecone_res = results
        
        # Process results & build context
        context = {
            "session": {},
            "profile": {},
            "relationships": [],
            "memories": []
        }
        
        # 1. Redis (Session)
        if isinstance(redis_res, MemoryFetchResult) and redis_res.found:
            context["session"] = redis_res.data
            debug_logs.append(f"✅ Redis: Found session context ({redis_res.query_time_ms:.1f}ms)")
        elif isinstance(redis_res, Exception):
            debug_logs.append(f"❌ Redis Error: {str(redis_res)}")
            
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
            
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        debug_logs.append(f"[Holographic Fetch END] Total time: {total_time:.1f}ms")
        
        return context, debug_logs
    
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
        """Fetch from MongoDB (structured memory + conversation history)"""
        start = datetime.now()
        
        try:
            # Query MongoDB for user's structured memory
            user_memory = await self.memory_collection.find_one({"userId": user_id})
            
            query_time = (datetime.now() - start).total_seconds() * 1000
            
            if user_memory:
                # Extract relevant fields
                memory_data = {
                    "name": user_memory.get("name"),
                    "interests": user_memory.get("interests", []),
                    "preferences": user_memory.get("preferences", []),
                    "profile": user_memory.get("profile", {}),
                }
                
                # Check if any relevant data exists
                has_data = (
                    memory_data["name"] or
                    len(memory_data["interests"]) > 0 or
                    len(memory_data["preferences"]) > 0 or
                    len(memory_data["profile"]) > 0
                )
                
                if has_data:
                    return MemoryFetchResult(
                        found=True,
                        source=MemorySource.MONGODB,
                        data=memory_data,
                        query_time_ms=query_time,
                        reason=f"Found structured memory for user {user_id}"
                    )
            
            return MemoryFetchResult(
                found=False,
                source=MemorySource.MONGODB,
                data=None,
                query_time_ms=query_time,
                reason="No structured memory found in MongoDB"
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
                        n.value as value,
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
        - Prioritize: Profile > Relationships > Memories > Session
        """
        debug_logs.append("[Master Prompt] Starting enrichment")
        
        if not any(context.values()):
            debug_logs.append("[Master Prompt] No context to inject - using base prompt")
            return base_prompt, debug_logs
        
        # Build memory context section
        memory_block = "[SYSTEM MEMORY CONTEXT]\n"
        
        # 1. Core Profile (MongoDB)
        if context.get("profile"):
            profile = context["profile"]
            memory_block += "👤 User Profile:\n"
            if profile.get("name"):
                memory_block += f"  - Name: {profile['name']}\n"
            if profile.get("interests"):
                memory_block += f"  - Interests: {', '.join(profile['interests'])}\n"
            if profile.get("preferences"):
                memory_block += f"  - Preferences: {', '.join(profile['preferences'])}\n"
            memory_block += "\n"
            
        # 2. Relationships (Neo4j)
        if context.get("relationships"):
            memory_block += "🕸️ Knowledge Graph:\n"
            for rel in context["relationships"]:
                memory_block += f"  - {rel['type']} → {rel['target']}\n"
            memory_block += "\n"
            
        # 3. Semantic Memories (Pinecone)
        if context.get("memories"):
            memory_block += "🧠 Relevant Memories:\n"
            for mem in context["memories"]:
                memory_block += f"  - {mem['text']} (confidence: {mem['score']:.2f})\n"
            memory_block += "\n"
            
        # 4. Session Context (Redis)
        if context.get("session"):
            memory_block += "⚡ Session Context:\n"
            for key, value in context["session"].items():
                if key != "timestamp":
                    memory_block += f"  - {key}: {value}\n"
            memory_block += "\n"
            
        memory_block += "[END SYSTEM MEMORY CONTEXT]\n\n"
        
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
        🎯 STORE MEMORY WITH SMART ROUTING
        
        Rules:
        - Route to correct system based on memory_type
        - Check for duplicates before storing
        - Confirm successful write
        - Skip temporary noise and system messages
        
        Debug logs show:
        - Why memory is being stored
        - Which system was chosen
        - What exact data is stored
        - Confirmation of successful write
        """
        debug_logs = []
        start_time = datetime.now()
        
        debug_logs.append(f"[Memory Storage START] user_id={user_id}, type={memory_type.value}")
        
        # Validation: Skip empty or trivial content
        if not memory_content or (isinstance(memory_content, str) and len(memory_content.strip()) < 3):
            debug_logs.append("[Memory Storage SKIP] Content too short or empty")
            return MemoryStorageResult(
                success=False,
                destination=None,
                memory_type=memory_type,
                reason="Content validation failed - too short or empty"
            ), debug_logs
        
        # Route to appropriate storage system
        if memory_type == MemoryType.SESSION:
            result = await self._store_to_redis(user_id, memory_content, metadata, debug_logs)
        
        elif memory_type in [MemoryType.CONVERSATION, MemoryType.PROFILE, MemoryType.PREFERENCE]:
            result = await self._store_to_mongodb(user_id, memory_content, memory_type, metadata, debug_logs)
        
        elif memory_type == MemoryType.RELATIONSHIP:
            result = await self._store_to_neo4j(user_id, memory_content, metadata, debug_logs)
        
        elif memory_type == MemoryType.SEMANTIC:
            result = await self._store_to_pinecone(user_id, memory_content, metadata, debug_logs)
        
        else:
            debug_logs.append(f"[Memory Storage ERROR] Unknown memory type: {memory_type}")
            return MemoryStorageResult(
                success=False,
                destination=None,
                memory_type=memory_type,
                reason=f"Unknown memory type: {memory_type}"
            ), debug_logs
        
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        debug_logs.append(f"[Memory Storage END] total_time={total_time:.2f}ms, success={result.success}")
        
        return result, debug_logs
    
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
                    MERGE (t:Entity {{name: $target_value}})
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
        
        # Step 2: Fetch memory (stop-on-hit)
        all_debug_logs.append("")
        memory_data, fetch_logs = await self.fetch_memory(user_id, message, intent)
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
            "which ", "what game", "what do i like", "what do i love"
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


# Global singleton instance
unified_memory_orchestrator = UnifiedMemoryOrchestrator()
