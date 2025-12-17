# Advanced Memory Manager for User Data and Memories
# Handles MongoDB, Redis, Pinecone, and Neo4j for unified user memory access and updates

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

from app.db.mongo_client import MongoClient
from app.db.redis_client import RedisClient
from app.utils.retry import retry_mongodb, retry_redis, retry_neo4j, retry_pinecone  # 🚀 Part 18
from app.db.neo4j_client import AdvancedNeo4jClient, PineconeClient
from app.services.pending_memory_service import (
    save_draft_memory,
    get_draft_memories,
)

logger = logging.getLogger(__name__)

class AdvancedMemoryManager:
    """
    Centralized memory manager that provides the AI model with full control over user data and memories.
    Implements all the safety rules: user validation, duplicate prevention, access control.
    """
    
    def __init__(self):
        self.mongo_client = MongoClient()
        self.redis_client = RedisClient()
        self.neo4j_client = AdvancedNeo4jClient()
        self.pinecone_client = PineconeClient()
    
    async def validate_user_access(self, user_id: str, session_token: Optional[str] = None) -> bool:
        """
        Validates that the user has proper access rights.
        Rule 3: Model should only modify the correct user
        """
        if not user_id:
            logger.warning("Invalid user_id provided")
            return False
        
        try:
            # Check if user exists in MongoDB
            user_profile = await self.get_user_profile(user_id)
            if not user_profile:
                logger.warning(f"User not found in database: {user_id}")
                return False
            
            # TODO: Implement session token validation
            # if session_token:
            #     session_valid = await self.validate_session_token(user_id, session_token)
            #     if not session_valid:
            #         logger.warning(f"Invalid session token for user: {user_id}")
            #         return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating user access: {str(e)}")
            return False
    
    async def load_user_memory(self, user_id: str) -> Dict[str, Any]:
        """
        Loads ALL relevant user memory from MongoDB, Redis, Pinecone, and Neo4j.
        Returns a comprehensive dict for context injection into the AI model.
        
        🚀 Part 12: MEMORY FALLBACK STRATEGY
        - Neo4j fails → use Redis
        - Redis fails → respond without session memory
        - Pinecone fails → skip deep memory
        - NEVER say "I don't know" due to infra errors!
        """
        if not self.validate_user_access(user_id):
            raise ValueError("Invalid user access")
        
        logger.info(f"Loading complete memory for user: {user_id}")
        
        try:
            # Validate user access first
            if not await self.validate_user_access(user_id):
                raise ValueError("Invalid user access")
                
            # MongoDB: Profile + Structured Memory + Tasks (CRITICAL - with retry)
            # 🚀 Part 18: Retry MongoDB operations (max 2 retries with exponential backoff)
            profile = await retry_mongodb(
                lambda: self.get_user_profile(user_id),
                f"Get user profile for {user_id}"
            ) or {}
            
            structured_memory = await retry_mongodb(
                lambda: self.get_structured_memory(user_id),
                f"Get structured memory for {user_id}"
            ) or []
            
            tasks = await retry_mongodb(
                lambda: self.get_user_tasks(user_id),
                f"Get tasks for {user_id}"
            ) or []
            
            conversations = await retry_mongodb(
                lambda: self.get_recent_conversations(user_id),
                f"Get conversations for {user_id}"
            ) or []
            
            # 🚀 Part 12: Redis with fallback
            # 🚀 Part 18: Retry Redis operations (max 1 retry, fast fail)
            temp_memory = {}
            session_state = {}
            try:
                temp_memory = await retry_redis(
                    lambda: self.get_temp_memory(user_id),
                    f"Get temp memory for {user_id}"
                ) or {}
                
                session_state = await retry_redis(
                    lambda: self.get_session_state(user_id),
                    f"Get session state for {user_id}"
                ) or {}
            except Exception as redis_error:
                logger.warning(f"⚠️ Redis failed after retries, responding without session memory: {redis_error}")
                # Fallback: Use empty state, continue without session memory
                temp_memory = {}
                session_state = {}
            
            # 🚀 Part 12: Pinecone with fallback
            # 🚀 Part 18: Retry Pinecone operations (max 1 retry, optional service)
            vector_memories = []
            try:
                vector_memories = await retry_pinecone(
                    lambda: self.get_vector_memories(user_id),
                    f"Get vector memories for {user_id}"
                ) or []
            except Exception as pinecone_error:
                logger.warning(f"⚠️ Pinecone failed after retries, skipping deep memory: {pinecone_error}")
                # Fallback: Use empty vector memories, continue without deep memory
                vector_memories = []
            
            # 🚀 Part 12: Neo4j with fallback to Redis
            # 🚀 Part 18: Retry Neo4j operations (max 2 retries)
            graph_relationships = []
            user_interests = []
            try:
                graph_relationships = await retry_neo4j(
                    lambda: self.get_graph_relationships(user_id),
                    f"Get graph relationships for {user_id}"
                ) or []
                
                user_interests = await retry_neo4j(
                    lambda: self.get_user_interests_graph(user_id),
                    f"Get user interests for {user_id}"
                ) or []
            except Exception as neo4j_error:
                logger.warning(f"⚠️ Neo4j failed after retries, trying Redis fallback: {neo4j_error}")
                # Fallback 1: Try to get from Redis
                try:
                    cached_graph = await retry_redis(
                        lambda: self.redis_client.get_user_data(user_id, "graph_cache"),
                        f"Get cached graph for {user_id}"
                    )
                    if cached_graph:
                        graph_relationships = cached_graph.get("relationships", [])
                        user_interests = cached_graph.get("interests", [])
                        logger.info("✅ Using Redis fallback for Neo4j data")
                except Exception as redis_fallback_error:
                    logger.warning(f"⚠️ Redis fallback also failed: {redis_fallback_error}")
                    # Final fallback: Empty data, but continue
                    graph_relationships = []
                    user_interests = []
            
            return {
                "profile": profile,
                "structured_memory": structured_memory,
                "tasks": tasks,
                "conversations": conversations,
                "temp_memory": temp_memory,
                "session_state": session_state,
                "vector_memories": vector_memories,
                "graph_relationships": graph_relationships,
                "interests": user_interests,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error loading user memory for {user_id}: {str(e)}")
            return {}
    
    async def process_memory_update_instructions(self, user_id: str, instructions: Dict[str, Any]) -> Dict[str, bool]:
        """
        Processes "Memory Update Instructions" from the AI model safely.
        Rule 4: Use "Memory Update Instructions" - Model doesn't write directly.
        
        Expected instruction format:
        {
            "updateMongo": { "location": "Bangalore" },
            "addStructuredMemory": { "type": "location", "value": "Bangalore" },
            "addVectorMemory": "I live in Bangalore",
            "addGraphMemory": ["LIVES_IN", "Bangalore"],
            "addTempMemory": { "recent_location_change": true }
        }
        """
        if not await self.validate_user_access(user_id):
            raise ValueError("Invalid user access")
        
        results = {}
        logger.info(f"Processing memory update instructions for user: {user_id}")
        
        try:
            # MongoDB Profile Updates
            if "updateMongo" in instructions:
                results["updateMongo"] = await self.update_user_profile(user_id, instructions["updateMongo"])
            
            # MongoDB Structured Memory
            if "addStructuredMemory" in instructions:
                results["addStructuredMemory"] = await self.add_structured_memory(user_id, instructions["addStructuredMemory"])
            
            # MongoDB Task Updates
            if "updateTask" in instructions:
                results["updateTask"] = await self.update_user_task(user_id, instructions["updateTask"])
            
            # Pinecone Vector Memory
            if "addVectorMemory" in instructions:
                results["addVectorMemory"] = await self.add_vector_memory(user_id, instructions["addVectorMemory"])
            
            # Neo4j Graph Memory
            if "addGraphMemory" in instructions:
                relation_type, target_value = instructions["addGraphMemory"]
                results["addGraphMemory"] = await self.add_graph_relationship(user_id, relation_type, target_value)
            
            # Redis Temporary Memory
            if "addTempMemory" in instructions:
                results["addTempMemory"] = await self.add_temp_memory(user_id, instructions["addTempMemory"])
            
            # Session State Updates
            if "updateSessionState" in instructions:
                results["updateSessionState"] = await self.update_session_state(user_id, instructions["updateSessionState"])
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing memory updates for {user_id}: {str(e)}")
            return {"error": str(e)}
    
    # MongoDB Operations
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile from MongoDB"""
        try:
            return await self.mongo_client.get_user_profile(user_id) or {}
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return {}
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile in MongoDB (Rule 2: Prevent duplicates - use update not insert)"""
        try:
            return await self.mongo_client.update_user_profile(user_id, updates)
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return False
    
    async def get_structured_memory(self, user_id: str) -> List[Dict[str, Any]]:
        """Get structured memories from MongoDB"""
        try:
            return await self.mongo_client.get_structured_memories(user_id) or []
        except Exception as e:
            logger.error(f"Error getting structured memory: {str(e)}")
            return []
    
    async def add_structured_memory(self, user_id: str, memory: Dict[str, Any]) -> bool:
        """
        Add structured memory to MongoDB with duplicate prevention.
        If MongoDB write fails, memory is stored as a pending draft instead of being lost.
        """
        try:
            # Rule 2: Prevent duplicates - check if memory already exists
            existing_memories = await self.get_structured_memory(user_id)
            for existing in existing_memories:
                if (
                    existing.get("type") == memory.get("type")
                    and existing.get("value") == memory.get("value")
                ):
                    logger.info(
                        f"Duplicate structured memory detected for user {user_id}, skipping"
                    )
                    return True

            memory["timestamp"] = datetime.now().isoformat()
            memory["user_id"] = user_id

            ok = await self.mongo_client.add_structured_memory(user_id, memory)
            if not ok:
                # Mongo failed – keep it as pending so it's never lost
                await save_draft_memory(
                    user_id=user_id,
                    memory_type=memory.get("type", "STRUCTURED"),
                    value=memory.get("value"),
                    source="structured_memory",
                    targets=[],
                )
            return ok
        except Exception as e:
            logger.error(f"Error adding structured memory: {str(e)}")
            # Best‑effort fallback to pending memory
            try:
                await save_draft_memory(
                    user_id=user_id,
                    memory_type=memory.get("type", "STRUCTURED"),
                    value=memory.get("value"),
                    source="structured_memory_error",
                    targets=[],
                )
            except Exception as inner:
                logger.error(f"Failed to save structured memory as draft: {inner}")
            return False
    
    async def get_user_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user tasks from MongoDB"""
        try:
            return await self.mongo_client.get_user_tasks(user_id) or []
        except Exception as e:
            logger.error(f"Error getting user tasks: {str(e)}")
            return []
    
    async def update_user_task(self, user_id: str, task_data: Dict[str, Any]) -> bool:
        """Update or create user task"""
        try:
            return await self.mongo_client.update_user_task(user_id, task_data)
        except Exception as e:
            logger.error(f"Error updating user task: {str(e)}")
            return False
    
    async def get_recent_conversations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversations from MongoDB"""
        try:
            return await self.mongo_client.get_recent_conversations(user_id, limit) or []
        except Exception as e:
            logger.error(f"Error getting recent conversations: {str(e)}")
            return []
    
    # Redis Operations
    async def get_temp_memory(self, user_id: str) -> Dict[str, Any]:
        """Get temporary memory from Redis"""
        try:
            return await self.redis_client.get_temp_memory(user_id) or {}
        except Exception as e:
            logger.error(f"Error getting temp memory: {str(e)}")
            return {}
    
    async def add_temp_memory(self, user_id: str, memory: Dict[str, Any]) -> bool:
        """Add temporary memory to Redis"""
        try:
            return await self.redis_client.set_temp_memory(user_id, memory)
        except Exception as e:
            logger.error(f"Error adding temp memory: {str(e)}")
            return False
    
    async def get_session_state(self, user_id: str) -> Dict[str, Any]:
        """Get session state from Redis"""
        try:
            return await self.redis_client.get_session_state(user_id) or {}
        except Exception as e:
            logger.error(f"Error getting session state: {str(e)}")
            return {}
    
    async def update_session_state(self, user_id: str, state: Dict[str, Any]) -> bool:
        """Update session state in Redis"""
        try:
            return await self.redis_client.update_session_state(user_id, state)
        except Exception as e:
            logger.error(f"Error updating session state: {str(e)}")
            return False
    
    # Pinecone Operations (Vector Memory)
    async def get_vector_memories(self, user_id: str) -> List[Dict[str, Any]]:
        """Get vector memories from Pinecone"""
        try:
            return await self.pinecone_client.get_user_memories(user_id) or []
        except Exception as e:
            logger.error(f"Error getting vector memories: {str(e)}")
            return []
    
    async def add_vector_memory(self, user_id: str, memory_text: str) -> bool:
        """
        Add vector memory to Pinecone with duplicate prevention.
        If Pinecone is unavailable, memory is stored as a draft to sync later.
        """
        try:
            # Rule 2: Prevent duplicates - check existing vectors
            existing_vectors = await self.get_vector_memories(user_id)
            for existing in existing_vectors:
                if existing.get("text", "").strip().lower() == memory_text.strip().lower():
                    logger.info(
                        f"Duplicate vector memory detected for user {user_id}, skipping"
                    )
                    return True

            ok = await self.pinecone_client.add_memory(user_id, memory_text)
            if not ok:
                await save_draft_memory(
                    user_id=user_id,
                    memory_type="VECTOR_MEMORY",
                    value=memory_text,
                    source="pinecone",
                    targets=["pinecone"],
                )
            return ok
        except Exception as e:
            logger.error(f"Error adding vector memory: {str(e)}")
            try:
                await save_draft_memory(
                    user_id=user_id,
                    memory_type="VECTOR_MEMORY",
                    value=memory_text,
                    source="pinecone_error",
                    targets=["pinecone"],
                )
            except Exception as inner:
                logger.error(f"Failed to save vector memory as draft: {inner}")
            return False
    
    # Neo4j Operations (Graph Relationships)
    async def get_graph_relationships(self, user_id: str) -> List[Dict[str, Any]]:
        """Get graph relationships from Neo4j
        🚀 Part 12: Cache to Redis for fallback
        """
        try:
            relationships = await self.neo4j_client.get_user_relationships(user_id) or []
            
            # 🚀 Part 12: Cache in Redis for fallback
            try:
                await self.redis_client.set_user_data(
                    user_id,
                    "graph_cache",
                    {"relationships": relationships, "cached_at": datetime.now().isoformat()},
                    ttl=1800  # 30 minutes
                )
            except Exception as cache_error:
                logger.warning(f"Failed to cache graph data to Redis: {cache_error}")
            
            return relationships
        except Exception as e:
            logger.error(f"Error getting graph relationships: {str(e)}")
            return []
    
    async def get_user_interests_graph(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user interests and connections from Neo4j
        🚀 Part 12: Cache to Redis for fallback
        """
        try:
            interests = await self.neo4j_client.get_user_interests(user_id) or []
            
            # 🚀 Part 12: Cache in Redis for fallback
            try:
                await self.redis_client.set_user_data(
                    user_id,
                    "interests_cache",
                    {"interests": interests, "cached_at": datetime.now().isoformat()},
                    ttl=1800  # 30 minutes
                )
            except Exception as cache_error:
                logger.warning(f"Failed to cache interests to Redis: {cache_error}")
            
            return interests
        except Exception as e:
            logger.error(f"Error getting user interests graph: {str(e)}")
            return []
    
    async def add_graph_relationship(
        self, user_id: str, relation_type: str, target_value: str
    ) -> bool:
        """
        Add graph relationship to Neo4j (Rule 2: MERGE).
        If Neo4j is down or slow, the relationship is stored as draft memory and
        will be synced later by the background job.
        """
        try:
            ok = await self.neo4j_client.merge_user_relationship(
                user_id, relation_type, target_value
            )
            if not ok:
                await save_draft_memory(
                    user_id=user_id,
                    memory_type="GRAPH_RELATIONSHIP",
                    value={"relation_type": relation_type, "target": target_value},
                    source="neo4j",
                    targets=["neo4j"],
                )
            return ok
        except Exception as e:
            logger.error(f"Error adding graph relationship: {str(e)}")
            try:
                await save_draft_memory(
                    user_id=user_id,
                    memory_type="GRAPH_RELATIONSHIP",
                    value={"relation_type": relation_type, "target": target_value},
                    source="neo4j_error",
                    targets=["neo4j"],
                )
            except Exception as inner:
                logger.error(f"Failed to save graph relationship as draft: {inner}")
            return False
    
    # Utility Methods
    def build_context_for_model(self, user_memory: Dict[str, Any]) -> str:
        """
        Build a comprehensive context string for the AI model from all user memories.
        This gives the model the "full picture" of the user.
        """
        context_parts = []
        
        # User Profile Context
        profile = user_memory.get('profile', {})
        if profile:
            context_parts.append(f"User Profile: {json.dumps(profile, indent=2)}")
        
        # Structured Memory Context
        structured = user_memory.get('structured_memory', [])
        if structured:
            context_parts.append(f"User Memories: {json.dumps(structured, indent=2)}")
        
        # Tasks Context
        tasks = user_memory.get('tasks', [])
        if tasks:
            context_parts.append(f"User Tasks: {json.dumps(tasks, indent=2)}")
        
        # Recent Conversations Context
        conversations = user_memory.get('conversations', [])
        if conversations:
            context_parts.append(f"Recent Conversations: {json.dumps(conversations[-5:], indent=2)}")
        
        # Interests and Relationships
        interests = user_memory.get('interests', [])
        if interests:
            context_parts.append(f"User Interests & Relationships: {json.dumps(interests, indent=2)}")
        
        # Session Context
        session = user_memory.get('session_state', {})
        if session:
            context_parts.append(f"Current Session: {json.dumps(session, indent=2)}")
        
        return "\n\n".join(context_parts)
    
    async def save_conversation(self, user_id: str, user_message: str, ai_response: str, memory_updates: Dict[str, Any] = None):
        """Save the conversation to MongoDB for future reference"""
        try:
            conversation_data = {
                "user_id": user_id,
                "user_message": user_message,
                "ai_response": ai_response,
                "timestamp": datetime.now().isoformat(),
                "memory_updates": memory_updates or {}
            }
            return await self.mongo_client.save_conversation(user_id, conversation_data)
        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")
            return False

# Global instance
memory_manager = AdvancedMemoryManager()