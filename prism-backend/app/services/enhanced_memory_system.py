"""
🧠 ENHANCED MEMORY SYSTEM - Unified Integration Layer
=====================================================

This module integrates all memory enhancement components into a single,
production-ready interface that works with the existing orchestrator.

Key Features:
- Strict user isolation (via MemoryGuard)
- Confidence-based storage and recall (via MemoryConfidence)
- Intelligent deduplication (via MemoryDeduplicator)
- Full observability (via MemoryObserver)
- Smart extraction (via EnhancedMemoryExtractor)

This is a NON-BREAKING enhancement layer that wraps existing functionality.

Usage:
    from app.services.enhanced_memory_system import EnhancedMemorySystem, enhanced_memory
    
    # Store with all protections
    result = await enhanced_memory.store(user_id, memory_data)
    
    # Recall with confidence prioritization
    memories = await enhanced_memory.recall(user_id, query)
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# Import enhancement modules
from app.services.memory_guard import (
    MemoryGuard, 
    memory_guard,
    MemoryOperation,
    MemoryAccessDenied,
    UserIdValidationError,
    require_user_isolation
)
from app.services.memory_confidence import (
    MemoryConfidence,
    memory_confidence,
    MemorySource,
    MemoryImportance,
    MemoryCategory
)
from app.services.memory_deduplication import (
    MemoryDeduplicator,
    memory_deduplicator,
    DuplicateType,
    MergeStrategy
)
from app.services.memory_observability import (
    MemoryObserver,
    memory_observer,
    OperationType,
    observe_memory_operation
)
from app.services.enhanced_memory_extractor import (
    EnhancedMemoryExtractor,
    memory_extractor
)

logger = logging.getLogger(__name__)


class EnhancedMemorySystem:
    """
    🧠 ENHANCED MEMORY SYSTEM
    
    Production-ready memory system with:
    - Zero cross-user contamination
    - Intelligent deduplication
    - Confidence-based prioritization
    - Full audit trail
    - Graceful degradation
    
    This wraps existing orchestrator functionality without breaking changes.
    """
    
    # 🆕 IDENTITY FIELDS - These should UPDATE, not duplicate
    IDENTITY_FIELDS = {"name", "age", "location", "occupation", "nickname", "email", "phone"}
    
    def __init__(self):
        # Initialize all enhancement modules
        self.guard = memory_guard
        self.confidence = memory_confidence
        self.deduplicator = memory_deduplicator
        self.observer = memory_observer
        self.extractor = memory_extractor
        
        # Get existing orchestrator (lazy load to avoid circular imports)
        self._orchestrator = None
        
        # Configuration
        self.MIN_CONFIDENCE_FOR_RECALL = 0.3    # Minimum confidence to include in recall
        self.MIN_CONFIDENCE_FOR_STORAGE = 0.5   # Minimum confidence to store
        self.MAX_MEMORIES_PER_RECALL = 20       # Maximum memories to return
        self.ENABLE_EXTRACTION = True           # Auto-extract from messages
        self.ENABLE_CONTRADICTION_DETECTION = True  # Detect and handle contradictions
        
        logger.info("🧠 EnhancedMemorySystem initialized")
    
    @property
    def orchestrator(self):
        """Lazy load orchestrator to avoid circular imports"""
        if self._orchestrator is None:
            try:
                from app.services.unified_memory_orchestrator import unified_memory_orchestrator
                self._orchestrator = unified_memory_orchestrator
            except ImportError:
                logger.warning("Could not import unified_memory_orchestrator")
                self._orchestrator = None
        return self._orchestrator
    
    async def store(
        self,
        user_id: str,
        memory_data: Dict[str, Any],
        memory_type: Optional[str] = None,
        source: Optional[str] = None,
        skip_dedup: bool = False
    ) -> Dict[str, Any]:
        """
        🔒 SECURE MEMORY STORAGE
        
        Stores memory with all protections:
        1. User isolation validation
        2. Content sanitization
        3. Deduplication check
        4. Confidence scoring
        5. Audit logging
        
        Args:
            user_id: User identifier (validated)
            memory_data: Memory content to store
            memory_type: Type of memory (optional)
            source: Source of memory (optional)
            skip_dedup: Skip deduplication check
            
        Returns:
            Storage result with status and metadata
        """
        start_time = time.time()
        result = {
            "success": False,
            "user_id": user_id,
            "action": "none",
            "message": "",
            "memory_id": None
        }
        
        try:
            # 1. VALIDATE USER ACCESS
            self.guard.validate_access(user_id, MemoryOperation.WRITE)
            
            # 2. SANITIZE CONTENT
            sanitized_data = self.guard.sanitize_memory_content(memory_data)
            
            # 3. ADD USER SCOPE
            scoped_data = self.guard.scope_document(user_id, sanitized_data)
            
            # 4. ENRICH WITH METADATA
            if source:
                scoped_data["source"] = source
            if memory_type:
                scoped_data["type"] = memory_type
            
            enriched_data = self.confidence.enrich_memory(scoped_data)
            
            # 5. CHECK CONFIDENCE THRESHOLD
            if enriched_data.get("confidence", 0) < self.MIN_CONFIDENCE_FOR_STORAGE:
                result["message"] = f"Confidence too low: {enriched_data.get('confidence', 0):.2f}"
                result["action"] = "rejected_low_confidence"
                logger.info(f"⚠️ Memory rejected (low confidence): {enriched_data.get('confidence', 0):.2f}")
                
                # Log as rejected but not error
                self.observer.log_operation(
                    OperationType.STORE, user_id, True, 
                    (time.time() - start_time) * 1000,
                    details={"action": "rejected_low_confidence"}
                )
                return result
            
            # 6. DEDUPLICATION CHECK
            if not skip_dedup:
                existing_memories = await self._get_existing_memories(user_id, memory_type)
                
                dup_type, existing, similarity = self.deduplicator.check_duplicate(
                    enriched_data, existing_memories, memory_type
                )
                
                if dup_type != DuplicateType.UNRELATED and existing:
                    # Handle duplicate
                    strategy = self.deduplicator.get_merge_strategy(
                        dup_type, enriched_data, existing
                    )
                    
                    if strategy == MergeStrategy.KEEP_EXISTING:
                        result["action"] = "duplicate_kept_existing"
                        result["message"] = f"Duplicate detected (similarity: {similarity:.2f})"
                        result["success"] = True
                        
                        self.observer.log_operation(
                            OperationType.DEDUPE, user_id, True,
                            (time.time() - start_time) * 1000,
                            details={"strategy": "keep_existing", "similarity": similarity}
                        )
                        return result
                    
                    elif strategy == MergeStrategy.UPDATE_CONFIDENCE:
                        # Strengthen existing memory
                        strengthened = self.confidence.strengthen(existing, "confirm")
                        await self._update_memory(user_id, existing, strengthened)
                        
                        result["action"] = "duplicate_strengthened"
                        result["message"] = f"Existing memory strengthened (confidence: {strengthened.get('confidence', 0):.2f})"
                        result["success"] = True
                        
                        self.observer.log_operation(
                            OperationType.UPDATE, user_id, True,
                            (time.time() - start_time) * 1000,
                            details={"strategy": "strengthen"}
                        )
                        return result
                    
                    elif strategy == MergeStrategy.MERGE_APPEND:
                        # Merge memories
                        merged = self.deduplicator.merge_memories(existing, enriched_data, strategy)
                        await self._update_memory(user_id, existing, merged)
                        
                        result["action"] = "merged"
                        result["message"] = "Memory merged with existing"
                        result["success"] = True
                        
                        self.observer.log_operation(
                            OperationType.MERGE, user_id, True,
                            (time.time() - start_time) * 1000,
                            details={"strategy": "merge"}
                        )
                        return result
                    
                    elif strategy == MergeStrategy.REPLACE:
                        # Replace old with new
                        enriched_data["replaces"] = existing.get("_id") or existing.get("id")
                        enriched_data["version"] = existing.get("version", 1) + 1
                        # Fall through to normal storage
            
            # 7. STORE MEMORY
            memory_id = await self._store_to_backend(user_id, enriched_data, memory_type)
            
            result["success"] = True
            result["action"] = "stored"
            result["message"] = "Memory stored successfully"
            result["memory_id"] = memory_id
            result["confidence"] = enriched_data.get("confidence", 0)
            
            # Log success
            self.observer.log_operation(
                OperationType.STORE, user_id, True,
                (time.time() - start_time) * 1000,
                backend=self._get_backend_for_type(memory_type),
                details={"type": memory_type, "confidence": enriched_data.get("confidence", 0)}
            )
            
            logger.info(f"✅ Memory stored: user={user_id[:8]}..., type={memory_type}, confidence={enriched_data.get('confidence', 0):.2f}")
            
        except UserIdValidationError as e:
            result["message"] = f"Invalid user: {str(e)}"
            self.observer.log_operation(
                OperationType.STORE, user_id, False,
                (time.time() - start_time) * 1000,
                details={"error": "user_validation_failed"}
            )
            logger.error(f"❌ Memory store failed (invalid user): {e}")
            
        except MemoryAccessDenied as e:
            result["message"] = f"Access denied: {str(e)}"
            self.observer.log_operation(
                OperationType.STORE, user_id, False,
                (time.time() - start_time) * 1000,
                details={"error": "access_denied"}
            )
            logger.error(f"❌ Memory store failed (access denied): {e}")
            
        except Exception as e:
            result["message"] = f"Storage error: {str(e)}"
            self.observer.log_operation(
                OperationType.STORE, user_id, False,
                (time.time() - start_time) * 1000,
                details={"error": str(e)[:100]}
            )
            logger.error(f"❌ Memory store failed: {e}")
        
        return result
    
    async def recall(
        self,
        user_id: str,
        query: Optional[str] = None,
        memory_types: Optional[List[str]] = None,
        limit: int = None,
        min_confidence: float = None
    ) -> Dict[str, Any]:
        """
        🔍 SECURE MEMORY RECALL
        
        Retrieves memories with all protections:
        1. User isolation validation
        2. Confidence-based prioritization
        3. Relevance filtering
        4. Ownership verification
        
        Args:
            user_id: User identifier (validated)
            query: Optional query for relevance matching
            memory_types: Optional filter by types
            limit: Maximum memories to return
            min_confidence: Minimum confidence threshold
            
        Returns:
            Recall result with prioritized memories
        """
        start_time = time.time()
        result = {
            "success": False,
            "user_id": user_id,
            "memories": [],
            "count": 0,
            "message": ""
        }
        
        limit = limit or self.MAX_MEMORIES_PER_RECALL
        min_confidence = min_confidence or self.MIN_CONFIDENCE_FOR_RECALL
        
        try:
            # 1. VALIDATE USER ACCESS
            self.guard.validate_access(user_id, MemoryOperation.READ)
            
            # 2. FETCH FROM BACKEND
            raw_memories = await self._fetch_from_backend(user_id, query, memory_types)
            
            # 3. VERIFY OWNERSHIP
            verified_memories = []
            for memory in raw_memories:
                if self.guard.verify_ownership(user_id, memory):
                    verified_memories.append(memory)
                else:
                    logger.warning(f"🚨 Memory ownership verification failed")
            
            # 4. FILTER BY CONFIDENCE
            confident_memories = [
                m for m in verified_memories
                if m.get("confidence", 0.5) >= min_confidence
            ]
            
            # 5. PRIORITIZE
            prioritized = self.confidence.prioritize_memories(
                confident_memories, query, limit
            )
            
            # 6. STRENGTHEN accessed memories (background)
            for memory in prioritized:
                memory_strengthened = self.confidence.strengthen(memory, "access")
                # Note: In production, batch update these
            
            result["success"] = True
            result["memories"] = prioritized
            result["count"] = len(prioritized)
            result["message"] = f"Retrieved {len(prioritized)} memories"
            
            # Log success
            self.observer.log_operation(
                OperationType.FETCH, user_id, True,
                (time.time() - start_time) * 1000,
                details={"count": len(prioritized), "query": query[:50] if query else None}
            )
            
        except UserIdValidationError as e:
            result["message"] = f"Invalid user: {str(e)}"
            self.observer.log_operation(
                OperationType.FETCH, user_id, False,
                (time.time() - start_time) * 1000,
                details={"error": "user_validation_failed"}
            )
            
        except MemoryAccessDenied as e:
            result["message"] = f"Access denied: {str(e)}"
            self.observer.log_operation(
                OperationType.FETCH, user_id, False,
                (time.time() - start_time) * 1000,
                details={"error": "access_denied"}
            )
            
        except Exception as e:
            result["message"] = f"Recall error: {str(e)}"
            self.observer.log_operation(
                OperationType.FETCH, user_id, False,
                (time.time() - start_time) * 1000,
                details={"error": str(e)[:100]}
            )
            logger.error(f"❌ Memory recall failed: {e}")
        
        return result
    
    async def delete(
        self,
        user_id: str,
        memory_id: Optional[str] = None,
        delete_all: bool = False
    ) -> Dict[str, Any]:
        """
        🗑️ SECURE MEMORY DELETION
        
        Deletes memories with all protections.
        
        Args:
            user_id: User identifier (validated)
            memory_id: Specific memory to delete
            delete_all: Delete all user memories
            
        Returns:
            Deletion result
        """
        start_time = time.time()
        result = {
            "success": False,
            "user_id": user_id,
            "deleted_count": 0,
            "message": ""
        }
        
        try:
            # 1. VALIDATE USER ACCESS
            self.guard.validate_access(user_id, MemoryOperation.DELETE)
            
            if delete_all:
                # Delete all memories for user
                deleted_count = await self._delete_all_user_memories(user_id)
                result["deleted_count"] = deleted_count
                result["message"] = f"Deleted {deleted_count} memories"
            elif memory_id:
                # Delete specific memory (after ownership check)
                success = await self._delete_single_memory(user_id, memory_id)
                result["deleted_count"] = 1 if success else 0
                result["message"] = "Memory deleted" if success else "Memory not found"
            else:
                result["message"] = "Specify memory_id or delete_all=True"
                return result
            
            result["success"] = True
            
            self.observer.log_operation(
                OperationType.DELETE, user_id, True,
                (time.time() - start_time) * 1000,
                details={"deleted_count": result["deleted_count"]}
            )
            
        except Exception as e:
            result["message"] = f"Delete error: {str(e)}"
            self.observer.log_operation(
                OperationType.DELETE, user_id, False,
                (time.time() - start_time) * 1000,
                details={"error": str(e)[:100]}
            )
            logger.error(f"❌ Memory delete failed: {e}")
        
        return result
    
    async def process_message(
        self,
        user_id: str,
        message: str,
        auto_extract: bool = None
    ) -> Dict[str, Any]:
        """
        📝 PROCESS MESSAGE FOR MEMORY
        
        Extracts and stores memories from a user message.
        
        Args:
            user_id: User identifier
            message: User message to process
            auto_extract: Override extraction setting
            
        Returns:
            Processing result with extracted memories
        """
        auto_extract = auto_extract if auto_extract is not None else self.ENABLE_EXTRACTION
        
        result = {
            "success": False,
            "user_id": user_id,
            "extracted": [],
            "stored": [],
            "message": ""
        }
        
        try:
            # Check if message likely contains extractable info
            if not auto_extract or not self.extractor.should_extract_from_message(message):
                result["success"] = True
                result["message"] = "No extractable information detected"
                return result
            
            # Extract memories
            extractions = await self.extractor.extract(user_id, message)
            result["extracted"] = extractions
            
            # Store each extraction
            for extraction in extractions:
                store_result = await self.store(
                    user_id=user_id,
                    memory_data=extraction,
                    memory_type=extraction.get("category"),
                    source="conversation_extraction"
                )
                
                if store_result.get("success"):
                    result["stored"].append({
                        "type": extraction.get("category"),
                        "value": extraction.get("value"),
                        "action": store_result.get("action")
                    })
            
            result["success"] = True
            result["message"] = f"Extracted {len(extractions)}, stored {len(result['stored'])}"
            
        except Exception as e:
            result["message"] = f"Processing error: {str(e)}"
            logger.error(f"❌ Message processing failed: {e}")
        
        return result
    
    async def get_context_for_ai(
        self,
        user_id: str,
        query: str,
        intent: str = "general"
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        🤖 GET MEMORY CONTEXT FOR AI
        
        Retrieves relevant memory context for AI responses.
        This is the main integration point with the existing orchestrator.
        
        Args:
            user_id: User identifier
            query: Current user query
            intent: Detected intent
            
        Returns:
            Tuple of (context_dict, debug_logs)
        """
        debug_logs = []
        context = {
            "profile": {},
            "memories": [],
            "preferences": [],
            "relationships": [],
            "recent_context": []
        }
        
        try:
            # Validate user first
            self.guard.validate_access(user_id, MemoryOperation.READ)
            debug_logs.append(f"✅ User validation passed: {user_id[:8]}...")
            
            # Use existing orchestrator if available
            if self.orchestrator:
                orchestrator_context, orchestrator_logs = await self.orchestrator.get_holographic_context(
                    user_id=user_id,
                    query=query,
                    intent=intent
                )
                debug_logs.extend(orchestrator_logs)
                
                # Merge with enhanced context
                context["profile"] = orchestrator_context.get("profile", {})
                context["relationships"] = orchestrator_context.get("relationships", [])
                
                # Get additional memories with confidence filtering
                recall_result = await self.recall(
                    user_id=user_id,
                    query=query,
                    min_confidence=0.4,
                    limit=10
                )
                
                if recall_result.get("success"):
                    for mem in recall_result.get("memories", []):
                        context["memories"].append({
                            "text": mem.get("text") or mem.get("value"),
                            "type": mem.get("type") or mem.get("category"),
                            "confidence": mem.get("confidence", 0.5),
                            "priority_score": mem.get("_priority_score", 0.5)
                        })
                    
                    debug_logs.append(f"✅ Enhanced recall: {len(context['memories'])} memories")
            
            else:
                # Fallback: use enhanced system only
                recall_result = await self.recall(
                    user_id=user_id,
                    query=query,
                    min_confidence=0.3,
                    limit=15
                )
                
                if recall_result.get("success"):
                    for mem in recall_result.get("memories", []):
                        if mem.get("category") == "identity" or mem.get("type") == "profile":
                            context["profile"].update({
                                mem.get("type", "info"): mem.get("text") or mem.get("value")
                            })
                        elif mem.get("category") == "preference":
                            context["preferences"].append(mem)
                        elif mem.get("category") == "relationship":
                            context["relationships"].append(mem)
                        else:
                            context["memories"].append(mem)
                
                debug_logs.append(f"✅ Enhanced recall (fallback): {recall_result.get('count', 0)} memories")
            
        except UserIdValidationError as e:
            debug_logs.append(f"❌ User validation failed: {str(e)}")
        except MemoryAccessDenied as e:
            debug_logs.append(f"❌ Access denied: {str(e)}")
        except Exception as e:
            debug_logs.append(f"❌ Context error: {str(e)}")
            logger.error(f"Failed to get AI context: {e}")
        
        return context, debug_logs
    
    def get_health(self) -> Dict[str, Any]:
        """Get system health status"""
        return self.observer.get_health_status()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        return self.observer.get_metrics()
    
    def get_debug_info(self, user_id: str) -> Dict[str, Any]:
        """Get debug information for a user (for support)"""
        return self.observer.get_debug_snapshot(user_id)
    
    # ==========================================
    # PRIVATE HELPER METHODS
    # ==========================================
    
    async def _get_existing_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get existing memories for deduplication check"""
        try:
            if self.orchestrator:
                # Use orchestrator's MongoDB collection
                from app.db.mongo_client import memory_collection
                
                query = self.guard.scope_query(user_id, {})
                if memory_type:
                    query["type"] = memory_type
                
                cursor = memory_collection.find(query).limit(50)
                return await cursor.to_list(length=50)
            
            return []
        except Exception as e:
            logger.warning(f"Failed to get existing memories: {e}")
            return []
    
    async def _store_to_backend(
        self,
        user_id: str,
        memory_data: Dict[str, Any],
        memory_type: Optional[str]
    ) -> Optional[str]:
        """Store memory to appropriate backend"""
        try:
            if self.orchestrator:
                # Use orchestrator's storage methods
                from app.services.unified_memory_orchestrator import MemoryType
                
                mem_type = MemoryType.SEMANTIC  # Default
                
                # 🧠 IDENTITY DATA: Name, age, location -> Store to PROFILE
                profile_types = ["name", "nickname", "age", "location", "occupation", "identity", "profile"]
                
                if memory_type in profile_types:
                    mem_type = MemoryType.PROFILE
                    # 🆕 For profile data, structure it properly
                    if memory_type == "name":
                        memory_data = {"name": memory_data.get("value") or memory_data.get("text")}
                    elif memory_type == "age":
                        memory_data = {"age": memory_data.get("value") or memory_data.get("text")}
                    elif memory_type == "location":
                        memory_data = {"profile": {"location": memory_data.get("value") or memory_data.get("text")}}
                    elif memory_type == "occupation":
                        memory_data = {"occupation": memory_data.get("value") or memory_data.get("text")}
                        
                elif memory_type in ["preference", "interest", "hobby"]:
                    mem_type = MemoryType.PREFERENCE
                elif memory_type == "relationship":
                    mem_type = MemoryType.RELATIONSHIP
                elif memory_type == "session":
                    mem_type = MemoryType.SESSION
                
                result, logs = await self.orchestrator.store_memory(
                    user_id=user_id,
                    memory_content=memory_data.get("text") or memory_data.get("value") or memory_data,
                    memory_type=mem_type,
                    metadata=memory_data
                )
                
                # 🆕 ALSO update users_collection directly for profile data
                if mem_type == MemoryType.PROFILE and result.success:
                    await self._update_user_profile(user_id, memory_type, memory_data)
                
                return "stored" if result.success else None
            
            else:
                # Fallback: direct MongoDB storage
                from app.db.mongo_client import memory_collection
                
                result = await memory_collection.insert_one(memory_data)
                return str(result.inserted_id)
                
        except Exception as e:
            logger.error(f"Backend storage failed: {e}")
            return None
    
    async def _update_user_profile(
        self,
        user_id: str,
        memory_type: str,
        memory_data: Dict[str, Any]
    ):
        """
        🆕 DIRECTLY UPDATE USER PROFILE IN users_collection
        
        This ensures identity data (name, age, location) is stored where
        the recall system looks for it.
        
        Features:
        - Contradiction detection & logging
        - Automatic cache invalidation
        - Audit trail
        """
        try:
            from app.db.mongo_client import users_collection
            from bson import ObjectId
            
            # Convert user_id to ObjectId
            user_obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
            if not user_obj_id:
                logger.warning(f"⚠️ Invalid user_id for profile update: {user_id}")
                return
            
            # Build update based on memory type
            update_data = {}
            
            value = memory_data.get("value") or memory_data.get("text") or memory_data.get("name")
            
            if not value:
                return
            
            # �️ SAFEGUARD: Reject invalid placeholder values that should NEVER be stored
            invalid_values = {
                'unknown', 'none', 'null', 'undefined', 'n/a', 'na', 'nil',
                'not provided', 'not specified', 'not given', 'not set',
                'anonymous', 'user', 'guest', 'default', 'unspecified',
                'no name', 'no age', 'no location', '?', 'idk', 'i don\'t know'
            }
            
            if str(value).lower().strip() in invalid_values:
                logger.warning(f"🛑 [Profile] REJECTED invalid value '{value}' for {memory_type} - not storing")
                return
            
            # 🔍 Check for contradictions (will log if found)
            old_value = await self._check_and_log_contradiction(user_id, memory_type, value)
            
            # 🛡️ SAFEGUARD: Never overwrite a VALID name with an invalid/questionable one
            if memory_type == "name" and old_value:
                # If we already have a real name, don't overwrite with short/suspicious values
                old_clean = str(old_value).strip()
                new_clean = str(value).strip()
                
                # If old name looks real (has space = likely first+last name) and new doesn't
                if ' ' in old_clean and ' ' not in new_clean and len(new_clean) < 6:
                    logger.warning(f"🛑 [Profile] REJECTED downgrade: keeping '{old_value}' instead of '{value}'")
                    return
            
            if memory_type == "name" and value:
                update_data["name"] = value
                if old_value:
                    logger.info(f"🧠 [Profile] UPDATING name: '{old_value}' → '{value}' for user {user_id[:8]}...")
                else:
                    logger.info(f"🧠 [Profile] Setting name to: {value} for user {user_id[:8]}...")
                
            elif memory_type == "age" and value:
                update_data["age"] = value
                if old_value:
                    logger.info(f"🧠 [Profile] UPDATING age: '{old_value}' → '{value}' for user {user_id[:8]}...")
                else:
                    logger.info(f"🧠 [Profile] Setting age to: {value} for user {user_id[:8]}...")
                
            elif memory_type == "location" and value:
                update_data["profile.location"] = value
                if old_value:
                    logger.info(f"🧠 [Profile] UPDATING location: '{old_value}' → '{value}' for user {user_id[:8]}...")
                else:
                    logger.info(f"🧠 [Profile] Setting location to: {value} for user {user_id[:8]}...")
                
            elif memory_type == "occupation" and value:
                update_data["occupation"] = value
                if old_value:
                    logger.info(f"🧠 [Profile] UPDATING occupation: '{old_value}' → '{value}' for user {user_id[:8]}...")
                else:
                    logger.info(f"🧠 [Profile] Setting occupation to: {value} for user {user_id[:8]}...")
            
            if update_data:
                # 🕐 Add timestamp for tracking
                update_data["profile_updated_at"] = datetime.utcnow().isoformat()
                
                # 🚀 FIX: Use UPSERT to create document if it doesn't exist!
                # This is CRITICAL - users may exist only in sessions/JWT but not in users collection
                result = await users_collection.update_one(
                    {"_id": user_obj_id},
                    {"$set": update_data},
                    upsert=True  # 🆕 CREATE document if it doesn't exist!
                )
                
                if result.modified_count > 0 or result.upserted_id:
                    action = "Created new profile" if result.upserted_id else "Updated profile"
                    logger.info(f"✅ [Profile] {action}: {list(update_data.keys())} for user {user_id[:8]}...")
                    
                    # 🚀 IMPORTANT: Clear cache so next fetch gets updated data
                    if self.orchestrator:
                        self.orchestrator._profile_cache.pop(user_id, None)
                        logger.info(f"🗑️ [Cache] Cleared profile cache for user {user_id[:8]}... after update")
                    else:
                        logger.warning(f"⚠️ [Cache] Could not clear cache - orchestrator not available")
                else:
                    logger.warning(f"⚠️ [Profile] No document modified for user {user_id[:8]}...")
                    
        except Exception as e:
            logger.error(f"❌ [Profile] Failed to update user profile: {e}")
    
    async def _check_and_log_contradiction(
        self,
        user_id: str,
        memory_type: str,
        new_value: str
    ) -> Optional[str]:
        """
        🔍 CHECK FOR CONTRADICTIONS
        
        Detects if new memory contradicts existing data.
        Returns the old value if contradiction detected, None otherwise.
        """
        if not self.ENABLE_CONTRADICTION_DETECTION:
            return None
            
        try:
            from app.db.mongo_client import users_collection
            from bson import ObjectId
            
            user_obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
            if not user_obj_id:
                return None
            
            # Fetch current profile
            user = await users_collection.find_one({"_id": user_obj_id})
            if not user:
                return None
            
            old_value = None
            
            if memory_type == "name":
                old_value = user.get("name")
            elif memory_type == "age":
                old_value = user.get("age")
            elif memory_type == "location":
                profile = user.get("profile", {})
                old_value = profile.get("location") if isinstance(profile, dict) else None
            elif memory_type == "occupation":
                old_value = user.get("occupation")
            
            # Check if there's a meaningful change
            if old_value and str(old_value).lower() != str(new_value).lower():
                logger.info(f"🔄 [Contradiction] {memory_type}: '{old_value}' → '{new_value}' for user {user_id[:8]}...")
                
                # Log the change for audit trail
                self.observer.log_operation(
                    OperationType.UPDATE, user_id, True, 0,
                    details={
                        "type": "memory_update",
                        "field": memory_type,
                        "old_value": str(old_value),
                        "new_value": new_value
                    }
                )
                
                return str(old_value)
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Contradiction check failed: {e}")
            return None
    
    async def get_memory_history(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        📜 GET MEMORY CHANGE HISTORY
        
        Returns history of memory changes for a user (audit trail).
        Combines data from:
        1. Observer's operation logs
        2. User profile with timestamps
        """
        try:
            history = []
            
            # Get from user profile
            from app.db.mongo_client import users_collection
            from bson import ObjectId
            
            user_obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
            if user_obj_id:
                user = await users_collection.find_one({"_id": user_obj_id})
                if user:
                    # Extract fields that exist in profile
                    fields_to_check = ["name", "age", "occupation"]
                    profile = user.get("profile", {})
                    
                    for field in fields_to_check:
                        if memory_type and memory_type != field:
                            continue
                        
                        value = user.get(field) or profile.get(field)
                        if value:
                            history.append({
                                "field": field,
                                "value": str(value),
                                "timestamp": user.get("profile_updated_at") or user.get("created_at"),
                                "type": "profile"
                            })
                    
                    # Check nested profile fields
                    if (not memory_type or memory_type == "location"):
                        loc = profile.get("location") or user.get("location")
                        if loc:
                            history.append({
                                "field": "location",
                                "value": str(loc),
                                "timestamp": user.get("profile_updated_at") or user.get("created_at"),
                                "type": "profile"
                            })
            
            return history[:limit]
            
        except Exception as e:
            logger.error(f"❌ Failed to get memory history: {e}")
            return []
    
    async def _fetch_from_backend(
        self,
        user_id: str,
        query: Optional[str],
        memory_types: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Fetch memories from backend"""
        try:
            memories = []
            
            if self.orchestrator:
                # Use orchestrator's holographic context
                context, _ = await self.orchestrator.get_holographic_context(
                    user_id=user_id,
                    query=query or "",
                    intent="history"
                )
                
                # Extract memories from context
                if context.get("profile"):
                    memories.append({
                        "type": "profile",
                        "user_id": user_id,
                        **context["profile"],
                        "confidence": 0.9
                    })
                
                for rel in context.get("relationships", []):
                    memories.append({
                        "type": "relationship",
                        "user_id": user_id,
                        **rel,
                        "confidence": rel.get("confidence", 0.7)
                    })
                
                for mem in context.get("memories", []):
                    memories.append({
                        "user_id": user_id,
                        **mem,
                        "confidence": mem.get("score", 0.5)
                    })
            
            # Also get from MongoDB directly
            from app.db.mongo_client import memory_collection
            
            mongo_query = self.guard.scope_query(user_id, {})
            if memory_types:
                mongo_query["type"] = {"$in": memory_types}
            
            cursor = memory_collection.find(mongo_query).limit(50)
            mongo_memories = await cursor.to_list(length=50)
            
            for mem in mongo_memories:
                mem["user_id"] = user_id  # Ensure user_id is set
                memories.append(mem)
            
            return memories
            
        except Exception as e:
            logger.error(f"Backend fetch failed: {e}")
            return []
    
    async def _update_memory(
        self,
        user_id: str,
        existing: Dict[str, Any],
        updated: Dict[str, Any]
    ):
        """Update an existing memory"""
        try:
            from app.db.mongo_client import memory_collection
            
            memory_id = existing.get("_id")
            if memory_id:
                await memory_collection.update_one(
                    {"_id": memory_id, "user_id": user_id},  # User scope
                    {"$set": updated}
                )
        except Exception as e:
            logger.error(f"Memory update failed: {e}")
    
    async def _delete_all_user_memories(self, user_id: str) -> int:
        """Delete all memories for a user"""
        try:
            from app.db.mongo_client import memory_collection
            
            result = await memory_collection.delete_many({"user_id": user_id})
            return result.deleted_count
        except Exception as e:
            logger.error(f"Delete all failed: {e}")
            return 0
    
    async def _delete_single_memory(self, user_id: str, memory_id: str) -> bool:
        """Delete a single memory (with ownership check)"""
        try:
            from app.db.mongo_client import memory_collection
            from bson import ObjectId
            
            result = await memory_collection.delete_one({
                "_id": ObjectId(memory_id),
                "user_id": user_id  # Ensure user owns this memory
            })
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Delete single failed: {e}")
            return False
    
    def _get_backend_for_type(self, memory_type: Optional[str]) -> str:
        """Determine which backend is used for a memory type"""
        if memory_type in ["session", "temp"]:
            return "redis"
        elif memory_type in ["relationship", "interest"]:
            return "neo4j"
        elif memory_type in ["semantic", "conversation"]:
            return "pinecone"
        else:
            return "mongodb"


# Global singleton instance
enhanced_memory = EnhancedMemorySystem()
