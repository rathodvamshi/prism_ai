"""
🚀 PRO MEMORY STORAGE SERVICE - Cross-System Memory Synchronization
====================================================================

This service ensures memories are stored across ALL relevant systems:
- MongoDB (structured data, profiles)
- Redis (session cache, quick access)
- Neo4j (relationships, graph)
- Pinecone (semantic search, embeddings)

🚀 PRO FEATURES:
- Automatic cross-pollination across all 4 systems
- Smart routing based on memory type
- Importance-based storage priority
- Memory update/correction handling
- Deduplication across systems
- Background sync for failed stores
- Memory consolidation and merging

Author: PRISM AI Team
"""

import logging
import asyncio
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class MemoryStorageTarget(Enum):
    """Target systems for memory storage"""
    MONGODB = "mongodb"
    REDIS = "redis"
    NEO4J = "neo4j"
    PINECONE = "pinecone"
    ALL = "all"


@dataclass
class MemoryStorageRequest:
    """Request to store a memory"""
    user_id: str
    category: str
    value: str
    confidence: float
    importance: float
    source: str
    original_text: Optional[str] = None
    is_update: bool = False
    targets: List[MemoryStorageTarget] = None
    
    def __post_init__(self):
        if self.targets is None:
            self.targets = [MemoryStorageTarget.ALL]


@dataclass
class StorageResult:
    """Result of a storage operation"""
    target: MemoryStorageTarget
    success: bool
    reason: str
    data_id: Optional[str] = None


class ProMemoryStorage:
    """
    🚀 PRO MEMORY STORAGE - Ensures memories reach ALL relevant systems
    
    Key Features:
    1. Smart routing based on memory category
    2. Parallel storage to multiple systems
    3. Automatic fallback and retry
    4. Memory update/correction handling
    5. Cross-pollination for comprehensive recall
    """
    
    # Category to storage targets mapping
    CATEGORY_TARGETS = {
        # Identity info -> ALL systems
        "name": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.REDIS, MemoryStorageTarget.NEO4J, MemoryStorageTarget.PINECONE],
        "nickname": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.REDIS, MemoryStorageTarget.NEO4J],
        "age": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.REDIS, MemoryStorageTarget.PINECONE],
        "birthday": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.REDIS],
        "location": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.REDIS, MemoryStorageTarget.NEO4J, MemoryStorageTarget.PINECONE],
        
        # Professional info -> MongoDB + Neo4j + Pinecone
        "occupation": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.NEO4J, MemoryStorageTarget.PINECONE],
        "skill": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.NEO4J, MemoryStorageTarget.PINECONE],
        "education": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.NEO4J, MemoryStorageTarget.PINECONE],
        "project": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.NEO4J, MemoryStorageTarget.PINECONE],
        
        # Interests/Preferences -> Neo4j (graph) + Pinecone (semantic)
        "interest": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.NEO4J, MemoryStorageTarget.PINECONE],
        "hobby": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.NEO4J, MemoryStorageTarget.PINECONE],
        "preference": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.NEO4J, MemoryStorageTarget.PINECONE],
        "dislike": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.NEO4J, MemoryStorageTarget.PINECONE],
        "food_preference": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.NEO4J, MemoryStorageTarget.PINECONE],
        
        # Relationships -> Neo4j primary + MongoDB backup
        "relationship": [MemoryStorageTarget.NEO4J, MemoryStorageTarget.MONGODB, MemoryStorageTarget.PINECONE],
        "family": [MemoryStorageTarget.NEO4J, MemoryStorageTarget.MONGODB],
        "pet": [MemoryStorageTarget.NEO4J, MemoryStorageTarget.MONGODB],
        
        # Goals -> Pinecone (for semantic recall) + MongoDB
        "goal": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.PINECONE, MemoryStorageTarget.NEO4J],
        
        # Languages -> MongoDB + Neo4j
        "language": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.NEO4J],
        
        # Schedule/Timezone -> Redis (quick access) + MongoDB
        "timezone": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.REDIS],
        "work_schedule": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.REDIS],
        
        # Communication style -> MongoDB + Redis
        "communication_style": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.REDIS],
        "learning_style": [MemoryStorageTarget.MONGODB, MemoryStorageTarget.REDIS],
        
        # Health/Contact -> MongoDB only (sensitive)
        "health_info": [MemoryStorageTarget.MONGODB],
        "contact_info": [MemoryStorageTarget.MONGODB],
        "financial_preference": [MemoryStorageTarget.MONGODB],
    }
    
    # Neo4j relationship type mapping
    NEO4J_RELATIONSHIP_MAP = {
        "interest": "INTERESTED_IN",
        "hobby": "ENJOYS",
        "preference": "PREFERS",
        "dislike": "DISLIKES",
        "skill": "HAS_SKILL",
        "location": "LIVES_IN",
        "occupation": "WORKS_AS",
        "project": "WORKING_ON",
        "goal": "AIMS_FOR",
        "relationship": "RELATED_TO",
        "family": "HAS_FAMILY_MEMBER",
        "pet": "OWNS_PET",
        "language": "SPEAKS",
        "education": "STUDIED",
    }
    
    def __init__(self):
        """Initialize with lazy-loaded services"""
        self._mongodb = None
        self._redis = None
        self._neo4j = None
        self._pinecone = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialize all services"""
        if self._initialized:
            return
        
        try:
            # MongoDB
            from app.db.mongo_client import db, users_collection, memory_collection
            self._mongodb = db
            self._users_collection = users_collection
            self._memory_collection = memory_collection
            
            # Redis
            from app.db.redis_client import redis_client
            self._redis = redis_client
            
            # Neo4j
            from app.db.neo4j_client import graph_memory, neo4j_client
            self._neo4j = neo4j_client
            self._graph_memory = graph_memory
            
            # Pinecone
            from app.services.vector_memory_service import get_vector_memory
            self._pinecone = get_vector_memory()
            
            self._initialized = True
            logger.info("🚀 ProMemoryStorage initialized with all services")
            
        except Exception as e:
            logger.error(f"❌ ProMemoryStorage initialization error: {e}")
    
    async def store_memory(
        self,
        request: MemoryStorageRequest,
        debug_logs: Optional[List[str]] = None
    ) -> List[StorageResult]:
        """
        🚀 MAIN ENTRY: Store memory across all relevant systems
        
        This is the PRO method that ensures comprehensive storage.
        """
        await self._ensure_initialized()
        
        if debug_logs is None:
            debug_logs = []
        
        debug_logs.append(f"[ProMemory] Storing {request.category}='{request.value}' (importance={request.importance})")
        
        # Determine storage targets
        targets = self._get_storage_targets(request)
        debug_logs.append(f"[ProMemory] Targets: {[t.value for t in targets]}")
        
        # Execute storage in parallel
        results = await self._parallel_store(request, targets, debug_logs)
        
        # Log results
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        if successful:
            debug_logs.append(f"[ProMemory] ✅ Stored to: {[r.target.value for r in successful]}")
        if failed:
            debug_logs.append(f"[ProMemory] ⚠️ Failed: {[f'{r.target.value}: {r.reason}' for r in failed]}")
            # Queue failed stores for background retry
            await self._queue_failed_stores(request, failed)
        
        return results
    
    def _get_storage_targets(self, request: MemoryStorageRequest) -> List[MemoryStorageTarget]:
        """Determine which systems should store this memory"""
        # If explicit targets provided (not ALL)
        if request.targets and MemoryStorageTarget.ALL not in request.targets:
            return request.targets
        
        # Get default targets for category
        category_targets = self.CATEGORY_TARGETS.get(
            request.category,
            [MemoryStorageTarget.MONGODB, MemoryStorageTarget.PINECONE]  # Default
        )
        
        # For high importance, add Redis for quick access
        if request.importance >= 0.8 and MemoryStorageTarget.REDIS not in category_targets:
            category_targets = [MemoryStorageTarget.REDIS] + category_targets
        
        return category_targets
    
    async def _parallel_store(
        self,
        request: MemoryStorageRequest,
        targets: List[MemoryStorageTarget],
        debug_logs: List[str]
    ) -> List[StorageResult]:
        """Store to multiple systems in parallel"""
        tasks = []
        
        for target in targets:
            if target == MemoryStorageTarget.MONGODB:
                tasks.append(self._store_to_mongodb(request, debug_logs))
            elif target == MemoryStorageTarget.REDIS:
                tasks.append(self._store_to_redis(request, debug_logs))
            elif target == MemoryStorageTarget.NEO4J:
                tasks.append(self._store_to_neo4j(request, debug_logs))
            elif target == MemoryStorageTarget.PINECONE:
                tasks.append(self._store_to_pinecone(request, debug_logs))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(StorageResult(
                    target=targets[i],
                    success=False,
                    reason=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _store_to_mongodb(
        self,
        request: MemoryStorageRequest,
        debug_logs: List[str]
    ) -> StorageResult:
        """Store to MongoDB with update handling"""
        try:
            from bson import ObjectId
            
            user_id = request.user_id
            
            # Build update document
            memory_doc = {
                "category": request.category,
                "value": request.value,
                "confidence": request.confidence,
                "importance": request.importance,
                "source": request.source,
                "original_text": request.original_text,
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            # Handle identity fields (name, age, location) - update user profile directly
            identity_fields = ["name", "nickname", "age", "location", "occupation", "timezone"]
            if request.category in identity_fields:
                # Update users collection profile
                profile_key = request.category
                if profile_key == "location":
                    profile_key = "profile.city"  # Store city in profile
                
                user_obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
                if user_obj_id:
                    update_result = await self._users_collection.update_one(
                        {"_id": user_obj_id},
                        {
                            "$set": {
                                profile_key: request.value,
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    debug_logs.append(f"[MongoDB] Updated user profile: {profile_key}={request.value}")
            
            # Also store in memory collection for structured retrieval
            memory_id = hashlib.md5(f"{user_id}:{request.category}:{request.value}".encode()).hexdigest()
            
            await self._memory_collection.update_one(
                {"userId": user_id, "category": request.category},
                {
                    "$set": memory_doc,
                    "$setOnInsert": {"memory_id": memory_id, "created_at": datetime.utcnow().isoformat()}
                },
                upsert=True
            )
            
            return StorageResult(
                target=MemoryStorageTarget.MONGODB,
                success=True,
                reason="Stored to MongoDB",
                data_id=memory_id
            )
            
        except Exception as e:
            logger.error(f"MongoDB storage error: {e}")
            return StorageResult(
                target=MemoryStorageTarget.MONGODB,
                success=False,
                reason=str(e)
            )
    
    async def _store_to_redis(
        self,
        request: MemoryStorageRequest,
        debug_logs: List[str]
    ) -> StorageResult:
        """Store to Redis for quick session access"""
        try:
            import json
            
            # Build session context key
            context_key = f"user:{request.user_id}:memory:{request.category}"
            
            data = {
                "value": request.value,
                "confidence": request.confidence,
                "importance": request.importance,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Store with 24-hour TTL for high importance, 1 hour otherwise
            ttl = 86400 if request.importance >= 0.8 else 3600
            
            await self._redis.setex(
                context_key,
                ttl,
                json.dumps(data)
            )
            
            # Also add to quick-access summary
            summary_key = f"user:{request.user_id}:memory_summary"
            await self._redis.hset(summary_key, request.category, request.value)
            await self._redis.expire(summary_key, 86400)  # 24 hour TTL
            
            debug_logs.append(f"[Redis] Stored {request.category} with {ttl}s TTL")
            
            return StorageResult(
                target=MemoryStorageTarget.REDIS,
                success=True,
                reason="Stored to Redis",
                data_id=context_key
            )
            
        except Exception as e:
            logger.error(f"Redis storage error: {e}")
            return StorageResult(
                target=MemoryStorageTarget.REDIS,
                success=False,
                reason=str(e)
            )
    
    async def _store_to_neo4j(
        self,
        request: MemoryStorageRequest,
        debug_logs: List[str]
    ) -> StorageResult:
        """Store to Neo4j as relationship"""
        try:
            if not self._neo4j.is_available:
                return StorageResult(
                    target=MemoryStorageTarget.NEO4J,
                    success=False,
                    reason="Neo4j not available"
                )
            
            # Get relationship type
            rel_type = self.NEO4J_RELATIONSHIP_MAP.get(request.category, "KNOWS")
            
            # Use dynamic relationship method
            result = await self._graph_memory.add_dynamic_relationship(
                user_id=request.user_id,
                target=request.value,
                relationship_type=rel_type,
                target_label=self._get_neo4j_label(request.category)
            )
            
            if result:
                debug_logs.append(f"[Neo4j] Created relationship: {rel_type} -> {request.value}")
                return StorageResult(
                    target=MemoryStorageTarget.NEO4J,
                    success=True,
                    reason="Stored to Neo4j",
                    data_id=f"{request.user_id}-{rel_type}-{request.value}"
                )
            else:
                return StorageResult(
                    target=MemoryStorageTarget.NEO4J,
                    success=False,
                    reason="Neo4j storage returned False"
                )
            
        except Exception as e:
            logger.error(f"Neo4j storage error: {e}")
            return StorageResult(
                target=MemoryStorageTarget.NEO4J,
                success=False,
                reason=str(e)
            )
    
    def _get_neo4j_label(self, category: str) -> str:
        """Get Neo4j node label for category"""
        label_map = {
            "interest": "Interest",
            "hobby": "Hobby",
            "preference": "Preference",
            "skill": "Skill",
            "location": "Location",
            "occupation": "Occupation",
            "project": "Project",
            "goal": "Goal",
            "language": "Language",
            "relationship": "Person",
            "family": "FamilyMember",
            "pet": "Pet",
            "education": "Education",
            "food_preference": "Food",
            "dislike": "Dislike",
        }
        return label_map.get(category, "Entity")
    
    async def _store_to_pinecone(
        self,
        request: MemoryStorageRequest,
        debug_logs: List[str]
    ) -> StorageResult:
        """Store to Pinecone with semantic deduplication"""
        try:
            if not self._pinecone or not self._pinecone.index:
                return StorageResult(
                    target=MemoryStorageTarget.PINECONE,
                    success=False,
                    reason="Pinecone not available"
                )
            
            # Create memory text for embedding
            memory_text = f"{request.category}: {request.value}"
            if request.original_text:
                memory_text += f" (from: {request.original_text[:100]})"
            
            # Store using vector memory service
            result = await self._pinecone.store_memory(
                user_id=request.user_id,
                text=memory_text,
                memory_type=request.category
            )
            
            if result:
                debug_logs.append(f"[Pinecone] Stored semantic memory: {request.category}")
                return StorageResult(
                    target=MemoryStorageTarget.PINECONE,
                    success=True,
                    reason="Stored to Pinecone"
                )
            else:
                return StorageResult(
                    target=MemoryStorageTarget.PINECONE,
                    success=False,
                    reason="Pinecone storage returned False"
                )
            
        except Exception as e:
            logger.error(f"Pinecone storage error: {e}")
            return StorageResult(
                target=MemoryStorageTarget.PINECONE,
                success=False,
                reason=str(e)
            )
    
    async def _queue_failed_stores(
        self,
        request: MemoryStorageRequest,
        failed_results: List[StorageResult]
    ):
        """Queue failed stores for background retry"""
        try:
            from app.services.pending_memory_service import save_draft_memory
            
            for result in failed_results:
                await save_draft_memory(
                    user_id=request.user_id,
                    memory_type=f"PRO_{request.category.upper()}",
                    value=request.value,
                    source=request.source,
                    targets=[result.target.value],
                    metadata={
                        "confidence": request.confidence,
                        "importance": request.importance,
                        "original_text": request.original_text,
                        "is_update": request.is_update,
                        "failed_reason": result.reason,
                    }
                )
            
            logger.info(f"Queued {len(failed_results)} failed stores for background retry")
            
        except Exception as e:
            logger.error(f"Failed to queue for retry: {e}")
    
    async def store_extracted_memories(
        self,
        user_id: str,
        extractions: List[Dict[str, Any]],
        debug_logs: Optional[List[str]] = None
    ) -> Dict[str, List[StorageResult]]:
        """
        🚀 PRO: Store multiple extracted memories from enhanced extractor
        
        This is the main method called after memory extraction.
        """
        await self._ensure_initialized()
        
        if debug_logs is None:
            debug_logs = []
        
        results = {}
        
        for extraction in extractions:
            request = MemoryStorageRequest(
                user_id=user_id,
                category=extraction.get("category", extraction.get("type", "unknown")),
                value=extraction.get("value", extraction.get("text", "")),
                confidence=extraction.get("confidence", 0.8) if isinstance(extraction.get("confidence"), (int, float)) else 0.8,
                importance=extraction.get("importance", 0.6),
                source=extraction.get("source", "extraction"),
                original_text=extraction.get("original_text"),
                is_update=extraction.get("is_update", False)
            )
            
            # Skip if value is empty
            if not request.value:
                continue
            
            storage_results = await self.store_memory(request, debug_logs)
            results[f"{request.category}:{request.value}"] = storage_results
        
        return results


# Global singleton
_pro_storage = None

def get_pro_memory_storage() -> ProMemoryStorage:
    """Get or create the ProMemoryStorage singleton"""
    global _pro_storage
    if _pro_storage is None:
        _pro_storage = ProMemoryStorage()
    return _pro_storage


# Convenience function
async def store_memories_pro(
    user_id: str,
    extractions: List[Dict[str, Any]],
    debug_logs: Optional[List[str]] = None
) -> Dict[str, List[StorageResult]]:
    """
    🚀 PRO Convenience function to store extracted memories across all systems
    """
    storage = get_pro_memory_storage()
    return await storage.store_extracted_memories(user_id, extractions, debug_logs)


async def quick_recall_user_memory(user_id: str) -> Dict[str, Any]:
    """
    🚀 PRO: Quick recall of all user memories from Redis cache
    
    This is a FAST method that returns cached user data for quick context building.
    Falls back to MongoDB if Redis cache miss.
    
    Returns:
        Dict with all cached user memory categories
    """
    storage = get_pro_memory_storage()
    await storage._ensure_initialized()
    
    result = {
        "user_id": user_id,
        "source": "cache",
        "memories": {}
    }
    
    try:
        # Try Redis first (fast path)
        summary_key = f"user:{user_id}:memory_summary"
        cached_summary = await storage._redis.hgetall(summary_key)
        
        if cached_summary:
            # Decode bytes to strings if needed
            for key, value in cached_summary.items():
                key_str = key.decode() if isinstance(key, bytes) else key
                value_str = value.decode() if isinstance(value, bytes) else value
                result["memories"][key_str] = value_str
            
            result["source"] = "redis_cache"
            logger.info(f"🚀 [Quick Recall] Cache hit for {user_id}: {len(result['memories'])} categories")
            return result
        
        # Cache miss - fall back to MongoDB
        from bson import ObjectId
        
        user_obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
        if user_obj_id:
            user_profile = await storage._users_collection.find_one(
                {"_id": user_obj_id},
                {"_id": 0, "name": 1, "email": 1, "age": 1, "occupation": 1, 
                 "interests": 1, "hobbies": 1, "profile": 1, "nickname": 1}
            )
            
            if user_profile:
                if user_profile.get("name"):
                    result["memories"]["name"] = user_profile["name"]
                if user_profile.get("nickname"):
                    result["memories"]["nickname"] = user_profile["nickname"]
                if user_profile.get("age"):
                    result["memories"]["age"] = str(user_profile["age"])
                if user_profile.get("occupation"):
                    result["memories"]["occupation"] = user_profile["occupation"]
                if user_profile.get("interests"):
                    result["memories"]["interests"] = ", ".join(user_profile["interests"][:5])
                if user_profile.get("hobbies"):
                    result["memories"]["hobbies"] = ", ".join(user_profile["hobbies"][:5])
                
                # Extract location from nested profile
                profile = user_profile.get("profile", {})
                if isinstance(profile, dict):
                    location_parts = [
                        profile.get("city"),
                        profile.get("state"),
                        profile.get("country")
                    ]
                    location = ", ".join([p for p in location_parts if p])
                    if location:
                        result["memories"]["location"] = location
                
                result["source"] = "mongodb"
                
                # Cache to Redis for next time (non-blocking)
                if result["memories"]:
                    try:
                        await storage._redis.hset(summary_key, mapping=result["memories"])
                        await storage._redis.expire(summary_key, 86400)  # 24 hour TTL
                    except:
                        pass  # Don't fail if caching fails
                
                logger.info(f"🚀 [Quick Recall] MongoDB lookup for {user_id}: {len(result['memories'])} categories")
        
        return result
        
    except Exception as e:
        logger.error(f"Quick recall error: {e}")
        return result


async def recall_user_identity(user_id: str) -> Dict[str, str]:
    """
    🚀 PRO: Recall just identity information (name, location, occupation)
    
    Super fast method for getting core identity data.
    """
    full_memory = await quick_recall_user_memory(user_id)
    
    identity = {}
    identity_keys = ["name", "nickname", "age", "location", "occupation", "timezone"]
    
    for key in identity_keys:
        if key in full_memory.get("memories", {}):
            identity[key] = full_memory["memories"][key]
    
    return identity
