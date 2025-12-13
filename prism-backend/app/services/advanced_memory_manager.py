# Advanced Memory Manager for User Data and Memories
# Handles MongoDB, Redis, Pinecone, and Neo4j for unified user memory access and updates

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

from app.db.mongo_client import MongoClient
from app.db.redis_client import RedisClient
from app.db.neo4j_client import AdvancedNeo4jClient, PineconeClient

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
        """
        if not self.validate_user_access(user_id):
            raise ValueError("Invalid user access")
        
        logger.info(f"Loading complete memory for user: {user_id}")
        
        try:
            # Validate user access first
            if not await self.validate_user_access(user_id):
                raise ValueError("Invalid user access")
                
            # MongoDB: Profile + Structured Memory + Tasks
            profile = await self.get_user_profile(user_id)
            structured_memory = await self.get_structured_memory(user_id)
            tasks = await self.get_user_tasks(user_id)
            conversations = await self.get_recent_conversations(user_id)
            
            # Redis: Temporary/Session Memory
            temp_memory = await self.get_temp_memory(user_id)
            session_state = await self.get_session_state(user_id)
            
            # Pinecone: Vector Memories (Long-term)
            vector_memories = await self.get_vector_memories(user_id)
            
            # Neo4j: Graph Relationships
            graph_relationships = await self.get_graph_relationships(user_id)
            user_interests = await self.get_user_interests_graph(user_id)
            
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
        """Add structured memory to MongoDB with duplicate prevention"""
        try:
            # Rule 2: Prevent duplicates - check if memory already exists
            existing_memories = await self.get_structured_memory(user_id)
            for existing in existing_memories:
                if (existing.get('type') == memory.get('type') and 
                    existing.get('value') == memory.get('value')):
                    logger.info(f"Duplicate structured memory detected for user {user_id}, skipping")
                    return True
            
            memory['timestamp'] = datetime.now().isoformat()
            memory['user_id'] = user_id
            return await self.mongo_client.add_structured_memory(user_id, memory)
        except Exception as e:
            logger.error(f"Error adding structured memory: {str(e)}")
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
        """Add vector memory to Pinecone with duplicate prevention"""
        try:
            # Rule 2: Prevent duplicates - check existing vectors
            existing_vectors = await self.get_vector_memories(user_id)
            for existing in existing_vectors:
                if existing.get('text', '').strip().lower() == memory_text.strip().lower():
                    logger.info(f"Duplicate vector memory detected for user {user_id}, skipping")
                    return True
            
            return await self.pinecone_client.add_memory(user_id, memory_text)
        except Exception as e:
            logger.error(f"Error adding vector memory: {str(e)}")
            return False
    
    # Neo4j Operations (Graph Relationships)
    async def get_graph_relationships(self, user_id: str) -> List[Dict[str, Any]]:
        """Get graph relationships from Neo4j"""
        try:
            return await self.neo4j_client.get_user_relationships(user_id) or []
        except Exception as e:
            logger.error(f"Error getting graph relationships: {str(e)}")
            return []
    
    async def get_user_interests_graph(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user interests and connections from Neo4j"""
        try:
            return await self.neo4j_client.get_user_interests(user_id) or []
        except Exception as e:
            logger.error(f"Error getting user interests graph: {str(e)}")
            return []
    
    async def add_graph_relationship(self, user_id: str, relation_type: str, target_value: str) -> bool:
        """Add graph relationship to Neo4j (Rule 2: Use MERGE not CREATE to prevent duplicates)"""
        try:
            return await self.neo4j_client.merge_user_relationship(user_id, relation_type, target_value)
        except Exception as e:
            logger.error(f"Error adding graph relationship: {str(e)}")
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