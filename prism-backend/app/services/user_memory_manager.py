"""
User-Isolated Memory Management System
Ensures complete separation of user data across all storage systems
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
import hashlib
import uuid
from app.db.mongo_client import users_collection, memory_collection
from app.db.redis_client import RedisClient
from app.db.neo4j_client import Neo4jClient
from app.services.vector_memory_service import get_vector_memory
from bson import ObjectId

logger = logging.getLogger(__name__)

class UserMemoryManager:
    """
    Manages user-specific memory storage with complete isolation.
    Each user's data is stored separately and securely.
    """
    
    def __init__(self):
        self.redis = RedisClient()
        self.neo4j = Neo4jClient()
        self.vector_memory = get_vector_memory()
    
    def _get_user_namespace(self, user_id: str, prefix: str = "") -> str:
        """Generate namespaced key for user data isolation"""
        return f"user:{user_id}:{prefix}" if prefix else f"user:{user_id}"
    
    def _get_memory_id(self, user_id: str, content: str, memory_type: str = "general") -> str:
        """Generate deterministic memory ID for user"""
        content_hash = hashlib.md5(f"{user_id}:{content}:{memory_type}".encode()).hexdigest()
        return f"mem_{user_id}_{content_hash[:12]}"
    
    async def save_conversation(self, user_id: str, user_message: str, ai_response: str) -> bool:
        """Save conversation with user isolation"""
        try:
            conversation_data = {
                "user_id": user_id,
                "user_message": user_message,
                "ai_response": ai_response,
                "timestamp": datetime.now(timezone.utc),
                "type": "conversation",
                "memory_id": self._get_memory_id(user_id, f"{user_message}_{ai_response}", "conversation")
            }
            
            # Save to MongoDB with user_id filter
            await memory_collection.insert_one(conversation_data)
            
            # Save to Redis for quick access
            redis_key = self._get_user_namespace(user_id, "recent_chat")
            await self.redis.lpush(redis_key, conversation_data)
            await self.redis.expire(redis_key, 86400)  # 24 hours
            
            # Save to vector memory with user filter
            if self.vector_memory and self.vector_memory.index:
                try:
                    combined_text = f"User: {user_message} Assistant: {ai_response}"
                    await self.vector_memory.store_memory(
                        user_id=user_id,
                        text=combined_text,
                        memory_type="conversation"
                    )
                except Exception as e:
                    logger.error(f"Failed to save to vector memory: {e}")
            
            # Save relationship to Neo4j
            try:
                await self.neo4j.add_conversation_node(user_id, user_message, ai_response)
            except Exception as e:
                logger.error(f"Failed to save to Neo4j: {e}")
            
            logger.info(f"Conversation saved for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save conversation for user {user_id}: {e}")
            return False
    
    async def save_user_preference(self, user_id: str, preference_type: str, preference_value: str) -> bool:
        """Save user preference with isolation"""
        try:
            preference_data = {
                "user_id": user_id,
                "preference_type": preference_type,
                "preference_value": preference_value,
                "timestamp": datetime.now(timezone.utc),
                "type": "preference",
                "memory_id": self._get_memory_id(user_id, f"{preference_type}_{preference_value}", "preference")
            }
            
            # Save to MongoDB
            await memory_collection.update_one(
                {"user_id": user_id, "preference_type": preference_type},
                {"$set": preference_data},
                upsert=True
            )
            
            # Cache in Redis
            redis_key = self._get_user_namespace(user_id, f"pref_{preference_type}")
            await self.redis.set(redis_key, preference_value, ex=86400 * 7)  # 7 days
            
            # Save to vector memory
            if self.vector_memory and self.vector_memory.index:
                try:
                    pref_text = f"User preference: {preference_type} is {preference_value}"
                    await self.vector_memory.store_memory(
                        user_id=user_id,
                        text=pref_text,
                        memory_type="preference"
                    )
                except Exception as e:
                    logger.error(f"Failed to save preference to vector memory: {e}")
            
            logger.info(f"Preference saved for user {user_id}: {preference_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save preference for user {user_id}: {e}")
            return False
    
    async def get_user_context(self, user_id: str, query: str = "", limit: int = 10) -> Dict[str, Any]:
        """Get user-specific context for AI responses"""
        try:
            context = {
                "conversations": [],
                "preferences": {},
                "memories": [],
                "user_profile": {}
            }
            
            # Get recent conversations from MongoDB
            recent_convos = await memory_collection.find(
                {"user_id": user_id, "type": "conversation"},
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit).to_list(length=limit)
            
            context["conversations"] = recent_convos
            
            # Get user preferences from Redis (faster)
            redis_pattern = self._get_user_namespace(user_id, "pref_*")
            try:
                pref_keys = await self.redis.keys(redis_pattern)
                for key in pref_keys:
                    pref_type = key.split(":")[-1].replace("pref_", "")
                    pref_value = await self.redis.get(key)
                    if pref_value:
                        context["preferences"][pref_type] = pref_value
            except Exception as e:
                logger.error(f"Error getting preferences from Redis: {e}")
            
            # Get relevant memories from vector search if query provided
            if query and self.vector_memory and self.vector_memory.index:
                try:
                    relevant_memories = await self.vector_memory.search_memories(
                        user_id=user_id,
                        query=query,
                        top_k=5
                    )
                    context["memories"] = relevant_memories
                except Exception as e:
                    logger.error(f"Error searching vector memories: {e}")
            
            # Get user profile from user collection
            try:
                user = await users_collection.find_one(
                    {"_id": ObjectId(user_id)},
                    {"password": 0, "passwordHash": 0, "otp": 0}  # Exclude sensitive data
                )
                if user:
                    context["user_profile"] = {
                        "email": user.get("email"),
                        "name": user.get("name"),
                        "profile": user.get("profile", {}),
                        "created_at": user.get("created_at"),
                        "preferences": user.get("preferences", {})
                    }
            except Exception as e:
                logger.error(f"Error getting user profile: {e}")
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get user context for {user_id}: {e}")
            return {"conversations": [], "preferences": {}, "memories": [], "user_profile": {}}
    
    async def delete_user_memories(self, user_id: str) -> Dict[str, Any]:
        """Delete all memories for a specific user with complete isolation"""
        try:
            deletion_results = {}
            
            # Delete from MongoDB
            mongo_result = await memory_collection.delete_many({"user_id": user_id})
            deletion_results["mongodb"] = {
                "deleted_count": mongo_result.deleted_count,
                "status": "success"
            }
            
            # Delete from Redis
            try:
                redis_pattern = self._get_user_namespace(user_id, "*")
                user_keys = await self.redis.keys(redis_pattern)
                if user_keys:
                    deleted_keys = await self.redis.delete(*user_keys)
                    deletion_results["redis"] = {
                        "deleted_keys": deleted_keys,
                        "status": "success"
                    }
                else:
                    deletion_results["redis"] = {
                        "deleted_keys": 0,
                        "status": "no_data"
                    }
            except Exception as e:
                deletion_results["redis"] = {
                    "error": str(e),
                    "status": "failed"
                }
            
            # Delete from vector memory
            try:
                if self.vector_memory and self.vector_memory.index:
                    await self.vector_memory.delete_user_memories(user_id)
                    deletion_results["vector_memory"] = {"status": "success"}
                else:
                    deletion_results["vector_memory"] = {"status": "not_available"}
            except Exception as e:
                deletion_results["vector_memory"] = {
                    "error": str(e),
                    "status": "failed"
                }
            
            # Delete from Neo4j
            try:
                await self.neo4j.delete_user_data(user_id)
                deletion_results["neo4j"] = {"status": "success"}
            except Exception as e:
                deletion_results["neo4j"] = {
                    "error": str(e),
                    "status": "failed"
                }
            
            logger.info(f"Memory deletion completed for user {user_id}")
            return deletion_results
            
        except Exception as e:
            logger.error(f"Failed to delete memories for user {user_id}: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def get_user_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for a specific user"""
        try:
            stats = {}
            
            # MongoDB stats
            conversation_count = await memory_collection.count_documents({
                "user_id": user_id, 
                "type": "conversation"
            })
            preference_count = await memory_collection.count_documents({
                "user_id": user_id, 
                "type": "preference"
            })
            
            stats["mongodb"] = {
                "conversations": conversation_count,
                "preferences": preference_count,
                "total": conversation_count + preference_count
            }
            
            # Redis stats
            try:
                redis_pattern = self._get_user_namespace(user_id, "*")
                user_keys = await self.redis.keys(redis_pattern)
                stats["redis"] = {
                    "cached_items": len(user_keys),
                    "available": True
                }
            except Exception as e:
                stats["redis"] = {
                    "available": False,
                    "error": str(e)
                }
            
            # Vector memory stats
            try:
                if self.vector_memory and self.vector_memory.index:
                    # This would require implementing a user-specific count in vector memory
                    stats["vector_memory"] = {
                        "available": True,
                        "note": "Vector memory stats require custom implementation"
                    }
                else:
                    stats["vector_memory"] = {"available": False}
            except Exception as e:
                stats["vector_memory"] = {
                    "available": False,
                    "error": str(e)
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get memory stats for user {user_id}: {e}")
            return {"error": str(e)}

# Global instance for use across the application
user_memory_manager = UserMemoryManager()

# Convenience functions for easy access
async def save_user_conversation(user_id: str, user_message: str, ai_response: str) -> bool:
    """Save user conversation with complete isolation"""
    return await user_memory_manager.save_conversation(user_id, user_message, ai_response)

async def save_user_preference(user_id: str, preference_type: str, preference_value: str) -> bool:
    """Save user preference with isolation"""
    return await user_memory_manager.save_user_preference(user_id, preference_type, preference_value)

async def get_user_ai_context(user_id: str, query: str = "") -> Dict[str, Any]:
    """Get user-specific context for AI responses"""
    return await user_memory_manager.get_user_context(user_id, query)

async def delete_all_user_memories(user_id: str) -> Dict[str, Any]:
    """Delete all user memories with complete isolation"""
    return await user_memory_manager.delete_user_memories(user_id)

async def get_user_memory_statistics(user_id: str) -> Dict[str, Any]:
    """Get memory statistics for user"""
    return await user_memory_manager.get_user_memory_stats(user_id)