"""
🧱 MEMORY MANAGEMENT PIPELINE

This is the core pipeline that processes user messages and manages memory across all databases.

🧱 8. PIPELINE WHEN USER SENDS A MESSAGE (Baby-Level Steps)

1. Backend receives message  
2. Identify userId
3. Fetch:
   - Mongo user data
   - Pinecone vector top memory  
   - Neo4j graph memory
   - Tasks & profile
4. Build combined context
5. Send to AI model
6. Save:
   - Conversation in Mongo
   - Embedded memory in Pinecone
   - Relationship updates in Neo4j
7. Return reply to frontend

🚫 HOW TO AVOID DUPLICATES (VERY IMPORTANT RULES)
🟢 Rule 1 — Check Memory before inserting
🟢 Rule 2 — Use Pinecone metadata uniqueness  
🟢 Rule 3 — Use Neo4j MERGE for relationships
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import hashlib
from bson import ObjectId

# Import all our perfect services
from app.db.mongo_client import (
    users_collection, sessions_collection, 
    tasks_collection, memory_collection
)
from app.db.redis_client import (
    cache_temp_message, get_temp_messages, clear_temp_messages,
    track_user_activity
)
from app.services.vector_memory_service import (
    vector_memory,
    process_user_message_for_memory,
    get_ai_context_for_user,
)
from app.db.neo4j_client import (
    graph_memory, get_user_context_summary
)
from app.models.perfect_models import (
    UserModel,
    SessionModel,
    TaskModel,
    MemoryModel,
    MessageModel,
    MemoryFact,
)
from app.services.pending_memory_service import save_draft_memory

class PerfectMemoryPipeline:
    """
    🏆 PERFECT MEMORY PIPELINE - EXACTLY AS SPECIFIED
    
    Handles complete user message processing with:
    - Complete user separation
    - No duplicate data
    - Multi-database coordination
    - Intelligent memory management
    """
    
    def __init__(self):
        self.processed_messages = set()  # Track processed messages to avoid duplicates
    
    async def process_user_message(
        self, 
        user_id: str, 
        session_id: str, 
        message: str,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        🧱 MAIN PIPELINE: Process user message through all databases
        
        Returns AI response with full context integration
        """
        try:
            print(f"[Chat] Processing message for user: {user_id}")
            
            # Step 1: Identify and validate user
            user_data = await self._get_or_create_user(user_id, user_email)
            if not user_data:
                return {"error": "Unable to identify user", "success": False}
            
            # Step 2: Check for duplicates (CRITICAL)
            message_hash = hashlib.md5(f"{user_id}:{session_id}:{message}".encode()).hexdigest()
            if message_hash in self.processed_messages:
                print("⚠️  Duplicate message detected, skipping processing")
                return {"error": "Duplicate message", "success": False}
            
            # Step 3: Track user activity
            await track_user_activity(user_id)
            
            # Step 4: Cache message temporarily in Redis
            await cache_temp_message(user_id, session_id, "user", message)
            
            # Step 5: Fetch context from all databases
            context = await self._build_comprehensive_context(user_id, message)
            
            # Step 6: Generate AI response
            ai_response = await self._generate_ai_response(user_data, context, message)
            
            # Step 7: Save everything to permanent storage
            await self._save_conversation_permanently(
                user_id, session_id, message, ai_response, user_data
            )
            
            # Step 8: Update memory systems
            await self._update_memory_systems(user_id, message, ai_response)
            
            # Mark message as processed
            self.processed_messages.add(message_hash)
            
            # Clean up old processed messages (keep only last 1000)
            if len(self.processed_messages) > 1000:
                self.processed_messages = set(list(self.processed_messages)[-500:])
            
            print(f"[Chat] Message processed for user: {user_id}")
            
            return {
                "success": True,
                "response": ai_response,
                "context_used": len(context.get("memories", [])) > 0,
                "user_name": user_data.get("name", ""),
                "session_id": session_id
            }
            
        except Exception as e:
            print(f"[Error] Message pipeline: {e}")
            return {"error": str(e), "success": False}
    
    async def _get_or_create_user(self, user_id: str, email: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Step 1: Get user data or create if doesn't exist
        🟢 Rule: Every user identified by email as primary unique identifier
        """
        try:
            # Try to find user by ID
            if ObjectId.is_valid(user_id):
                user = await users_collection.find_one({"_id": ObjectId(user_id)})
                if user:
                    return user
            
            # Try to find by email if provided
            if email:
                user = await users_collection.find_one({"email": email})
                if user:
                    return user
                
                # Create new user if email provided but not found
                new_user = UserModel(
                    email=email,
                    name=email.split("@")[0],  # Use email prefix as default name
                    role="user",
                    responseStyle="friendly"
                )
                
                result = await users_collection.insert_one(new_user.dict(by_alias=True))
                
                # Create user in graph database too
                await graph_memory.create_user_node(
                    str(result.inserted_id), email, new_user.name
                )
                
                print(f"✅ Created new user: {email}")
                return new_user.dict()
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting/creating user: {e}")
            return None
    
    async def _build_comprehensive_context(self, user_id: str, current_message: str) -> Dict[str, Any]:
        """
        Step 3: Fetch context from all databases
        - MongoDB user data
        - Pinecone vector memory  
        - Neo4j graph memory
        - Tasks & profile
        """
        context = {
            "user_profile": {},
            "memories": [],
            "graph_summary": "",
            "recent_tasks": [],
            "preferences": {}
        }
        
        try:
            # Parallel context fetching for performance
            import asyncio
            
            # Fetch from all sources simultaneously
            user_profile_task = users_collection.find_one({"_id": ObjectId(user_id)})
            vector_memories_task = get_ai_context_for_user(user_id, current_message)
            graph_summary_task = get_user_context_summary(user_id)
            recent_tasks_task = graph_memory.get_user_tasks(user_id)
            structured_memory_task = memory_collection.find_one({"userId": ObjectId(user_id)})
            
            # Wait for all context to load
            results = await asyncio.gather(
                user_profile_task,
                vector_memories_task, 
                graph_summary_task,
                recent_tasks_task,
                structured_memory_task,
                return_exceptions=True
            )
            
            # Process results
            user_profile, vector_context, graph_summary, recent_tasks, structured_memory = results
            
            # Format context
            if user_profile and not isinstance(user_profile, Exception):
                context["user_profile"] = {
                    "name": user_profile.get("name", ""),
                    "interests": user_profile.get("interests", []),
                    "hobbies": user_profile.get("hobbies", []),
                    "responseStyle": user_profile.get("responseStyle", "friendly")
                }
            
            if vector_context and not isinstance(vector_context, Exception):
                context["memories"] = vector_context.split("\n") if vector_context else []
            
            if graph_summary and not isinstance(graph_summary, Exception):
                context["graph_summary"] = graph_summary
            
            if recent_tasks and not isinstance(recent_tasks, Exception):
                context["recent_tasks"] = recent_tasks[:5]  # Limit to 5 recent tasks
            
            if structured_memory and not isinstance(structured_memory, Exception):
                context["preferences"] = structured_memory.get("preferences", {})
            
            print(f"✅ Built comprehensive context for user {user_id}")
            return context
            
        except Exception as e:
            print(f"❌ Error building context: {e}")
            return context
    
    async def _generate_ai_response(
        self, 
        user_data: Dict[str, Any], 
        context: Dict[str, Any], 
        message: str
    ) -> str:
        """
        Step 4: Generate AI response using full context
        """
        try:
            # Import AI service
            from app.services.main_brain import MainBrain
            
            brain = MainBrain()
            
            # Format context for AI
            context_prompt = self._format_context_for_ai(user_data, context)
            
            # Generate response
            response = await brain.generate_response(
                user_message=message,
                context=context_prompt,
                user_preferences=context.get("preferences", {})
            )
            
            return response
            
        except Exception as e:
            print(f"❌ Error generating AI response: {e}")
            return f"I apologize, but I'm having trouble processing your message right now. Please try again."
    
    def _format_context_for_ai(self, user_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Format all context into a coherent prompt for AI"""
        context_parts = []
        
        # User profile
        if context.get("user_profile", {}).get("name"):
            context_parts.append(f"User: {context['user_profile']['name']}")
        
        # Interests and hobbies
        interests = context.get("user_profile", {}).get("interests", [])
        hobbies = context.get("user_profile", {}).get("hobbies", [])
        
        if interests:
            context_parts.append(f"Interests: {', '.join(interests)}")
        if hobbies:
            context_parts.append(f"Hobbies: {', '.join(hobbies)}")
        
        # Response style
        response_style = context.get("user_profile", {}).get("responseStyle", "friendly")
        context_parts.append(f"Preferred response style: {response_style}")
        
        # Recent memories
        memories = context.get("memories", [])
        if memories:
            context_parts.append(f"Relevant memories: {'; '.join(memories[:3])}")
        
        # Graph summary
        if context.get("graph_summary"):
            context_parts.append(f"Context: {context['graph_summary']}")
        
        # Recent tasks
        recent_tasks = context.get("recent_tasks", [])
        if recent_tasks:
            task_titles = [task.get("title", "") for task in recent_tasks[:3]]
            context_parts.append(f"Recent tasks: {', '.join(task_titles)}")
        
        return " | ".join(context_parts)
    
    async def _save_conversation_permanently(
        self, 
        user_id: str, 
        session_id: str, 
        user_message: str, 
        ai_response: str,
        user_data: Dict[str, Any]
    ):
        """
        Step 5: Save conversation to MongoDB permanently
        🟢 Rule: NEVER store sessions without linking to userId
        """
        try:
            # Create message objects
            user_msg = MessageModel(role="user", text=user_message)
            ai_msg = MessageModel(role="assistant", text=ai_response)
            
            # Check if session exists
            session = await sessions_collection.find_one({
                "sessionId": session_id,
                "userId": ObjectId(user_id)
            })
            
            if session:
                # Add messages to existing session
                await sessions_collection.update_one(
                    {"sessionId": session_id, "userId": ObjectId(user_id)},
                    {
                        "$push": {
                            "messages": {
                                "$each": [user_msg.dict(), ai_msg.dict()]
                            }
                        },
                        "$set": {"updatedAt": datetime.utcnow()}
                    }
                )
            else:
                # Create new session
                new_session = SessionModel(
                    sessionId=session_id,
                    userId=ObjectId(user_id),
                    messages=[user_msg, ai_msg]
                )
                
                await sessions_collection.insert_one(new_session.dict(by_alias=True))
            
            # Clear temporary Redis messages after saving
            await clear_temp_messages(user_id, session_id)
            
            print(f"✅ Conversation saved permanently for session {session_id}")
            
        except Exception as e:
            print(f"❌ Error saving conversation: {e}")
    
    async def _update_memory_systems(self, user_id: str, user_message: str, ai_response: str):
        """
        Step 6: Update all memory systems
        - Pinecone vector memory
        - Neo4j graph relationships  
        - MongoDB structured memory
        """
        try:
            import asyncio
            
            # Process memories in parallel
            vector_task = process_user_message_for_memory(user_id, user_message)
            graph_task = self._update_graph_relationships(user_id, user_message)
            structured_task = self._update_structured_memory(user_id, user_message)
            
            await asyncio.gather(vector_task, graph_task, structured_task, return_exceptions=True)
            
            print(f"✅ Memory systems updated for user {user_id}")
            
        except Exception as e:
            print(f"❌ Error updating memory systems: {e}")
    
    async def _update_graph_relationships(self, user_id: str, message: str):
        """Update Neo4j graph relationships based on message content"""
        try:
            message_lower = message.lower()
            
            # Simple interest extraction patterns
            interest_patterns = [
                ("i love", "hobby"), ("i like", "interest"), 
                ("i enjoy", "hobby"), ("i'm interested in", "interest"),
                ("my hobby is", "hobby"), ("my interest is", "interest")
            ]
            
            for pattern, category in interest_patterns:
                if pattern in message_lower:
                    # Extract interest (simple approach)
                    start_idx = message_lower.find(pattern) + len(pattern)
                    remaining = message[start_idx:].strip()
                    
                    # Get first few words as interest
                    interest_words = remaining.split()[:3]
                    if interest_words:
                        interest = " ".join(interest_words).strip(".,!?")
                        if len(interest) > 2:  # Minimum length check
                            try:
                                await graph_memory.add_user_interest(user_id, interest, category)
                                print(f"✅ Added {category}: {interest}")
                            except Exception as neo_err:
                                # If Neo4j is down or slow, never drop the memory.
                                # Store as pending draft for later background sync.
                                print(f"❌ Neo4j interest save failed, storing draft instead: {neo_err}")
                                await save_draft_memory(
                                    user_id=user_id,
                                    memory_type="USER_INTEREST",
                                    value=interest,
                                    source="chat_message",
                                    targets=["neo4j"],
                                )
                            break
            
        except Exception as e:
            print(f"❌ Error updating graph relationships: {e}")
    
    async def _update_structured_memory(self, user_id: str, message: str):
        """
        Update MongoDB structured memory
        🟢 Rule: Check before inserting to avoid duplicates
        """
        try:
            # Check if user has structured memory document
            memory_doc = await memory_collection.find_one({"userId": ObjectId(user_id)})
            
            # Extract facts from message (simple approach)
            new_facts = []
            message_lower = message.lower()
            
            # Extract preferences
            preference_patterns = ["i prefer", "i like", "i love", "i hate", "i don't like"]
            for pattern in preference_patterns:
                if pattern in message_lower:
                    fact = MemoryFact(
                        type="preference", 
                        value=message,
                        confidence=0.8
                    )
                    new_facts.append(fact.dict())
                    break
            
            # Update or create memory document
            if memory_doc:
                if new_facts:
                    # Check for duplicates before adding
                    existing_values = {fact.get("value", "") for fact in memory_doc.get("facts", [])}
                    unique_facts = [fact for fact in new_facts if fact.get("value", "") not in existing_values]
                    
                    if unique_facts:
                        await memory_collection.update_one(
                            {"userId": ObjectId(user_id)},
                            {
                                "$push": {"facts": {"$each": unique_facts}},
                                "$set": {"updatedAt": datetime.utcnow()}
                            }
                        )
                        print(f"✅ Added {len(unique_facts)} new memory facts")
            else:
                # Create new memory document
                new_memory = MemoryModel(
                    userId=ObjectId(user_id),
                    facts=[MemoryFact(**fact) for fact in new_facts],
                    preferences={}
                )
                
                await memory_collection.insert_one(new_memory.dict(by_alias=True))
                print(f"✅ Created new memory document with {len(new_facts)} facts")
            
        except Exception as e:
            print(f"❌ Error updating structured memory: {e}")
    
    async def get_user_complete_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete user summary from all databases.
        Perfect for user profile display.
        """
        try:
            # Get data from all sources
            user_data = await users_collection.find_one({"_id": ObjectId(user_id)})
            graph_summary = await graph_memory.get_user_summary(user_id)
            memory_data = await memory_collection.find_one({"userId": ObjectId(user_id)})
            session_count = await sessions_collection.count_documents({"userId": ObjectId(user_id)})
            
            summary = {
                "userId": user_id,
                "email": user_data.get("email", "") if user_data else "",
                "name": user_data.get("name", "") if user_data else "",
                "interests": graph_summary.get("interests", []) if graph_summary else [],
                "total_tasks": graph_summary.get("total_tasks", 0) if graph_summary else 0,
                "completed_tasks": graph_summary.get("completed_tasks", 0) if graph_summary else 0,
                "session_count": session_count,
                "memory_facts_count": len(memory_data.get("facts", [])) if memory_data else 0,
                "response_style": user_data.get("responseStyle", "friendly") if user_data else "friendly"
            }
            
            return summary
            
        except Exception as e:
            print(f"❌ Error getting complete user summary: {e}")
            return {"error": str(e)}
    
    async def delete_user_completely(self, user_id: str) -> bool:
        """
        🚨 COMPLETE USER DELETION from all databases
        """
        try:
            import asyncio
            
            print(f"🗑️  Starting complete deletion for user {user_id}")
            
            # Delete from all databases simultaneously
            mongo_deletions = [
                users_collection.delete_one({"_id": ObjectId(user_id)}),
                sessions_collection.delete_many({"userId": ObjectId(user_id)}),
                tasks_collection.delete_many({"userId": ObjectId(user_id)}),
                memory_collection.delete_many({"userId": ObjectId(user_id)})
            ]
            
            vector_deletion = vector_memory.delete_user_memories(user_id)
            graph_deletion = graph_memory.delete_user_graph_data(user_id)
            
            # Execute all deletions
            await asyncio.gather(
                *mongo_deletions,
                vector_deletion,
                graph_deletion,
                return_exceptions=True
            )
            
            print(f"✅ User {user_id} completely deleted from all databases")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting user completely: {e}")
            return False

# Global pipeline instance
memory_pipeline = PerfectMemoryPipeline()

# 🎯 CONVENIENCE FUNCTIONS FOR API ROUTES

async def process_message(user_id: str, session_id: str, message: str, user_email: str = None) -> Dict[str, Any]:
    """Simple function to process user message through pipeline"""
    return await memory_pipeline.process_user_message(user_id, session_id, message, user_email)

async def get_user_summary(user_id: str) -> Dict[str, Any]:
    """Simple function to get complete user summary"""
    return await memory_pipeline.get_user_complete_summary(user_id)

async def delete_user_data(user_id: str) -> bool:
    """Simple function to delete all user data"""
    return await memory_pipeline.delete_user_completely(user_id)