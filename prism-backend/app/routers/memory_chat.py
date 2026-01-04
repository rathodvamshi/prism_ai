"""
🎯 MEMORY-ENHANCED CHAT ROUTER (SIMPLIFIED)

Focuses on the core memory management functionality without external dependencies.
from typing import Dict, Any, List
from bson import ObjectId
import json
import logging
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, Body

from app.services.advanced_memory_manager import memory_manager
from app.services.user_memory_manager import user_memory_manager, get_user_ai_context, save_user_conversation
from app.services.unified_memory_orchestrator import unified_memory_orchestrator, MemoryType, MemorySource
from app.services.main_brain import generate_response as main_brain_generate_response
from app.utils.auth import get_verified_user, SecurityUtils
from app.models.user_models import User
from app.db.mongo_client import users_collection
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/chat", 
    tags=["Memory Enhanced Chat"]
)

# 🔐 PROTECTED CHAT ENDPOINTS (JWT Required)

class ChatMessageRequest(BaseModel):
    message: str
    chat_id: str = None

class CreateChatRequest(BaseModel):
    title: str = None

@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_verified_user)
):
    """Send a message with user isolation and memory"""
    try:
        user_id = current_user.user_id
        user_email = current_user.email
        
        # Sanitize message input
        message = SecurityUtils.sanitize_user_input(request.message, 2000)
        
        logger.info(f"Chat message from user {user_email}: {message[:50]}...")
        
        # Load user-specific memory context with complete isolation
        user_context = await get_user_ai_context(user_id, message)
        
        # Generate response using main brain with user context
        response = await main_brain_generate_response(
            user_id=user_id,
            message=message,
            search_results=None,
            image_url=None
        )
        
        # Save conversation to user-isolated memory
        await save_user_conversation(user_id, message, response)
        
        # Store in MongoDB for chat history
        chat_entry = {
            "user_id": user_id,
            "chat_id": request.chat_id or "default",
            "message": message,
            "response": response,
            "timestamp": datetime.now(),
            "type": "chat",
            "message_id": str(ObjectId())
        }
        
        await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$push": {
                    "chat_history": {
                        "$each": [chat_entry],
                        "$slice": -100  # Keep only last 100 messages
                    }
                },
                "$set": {
                    "last_activity": datetime.now()
                }
            },
            upsert=True
        )
        
        logger.info(f"✅ Message processed and memories updated for user {user_id}")
        
        return {
            "response": response,
            "message_id": chat_entry["message_id"],
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "memory_updated": True,
            "chat_id": request.chat_id or "default"
        }
        
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )

@router.get("/history")
async def get_chat_history(
    chat_id: str = "default",
    limit: int = 50,
    current_user: User = Depends(get_verified_user)
):
    """Get user's chat history with proper isolation"""
    try:
        user_id = current_user.user_id
        
        # Get user document
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return {"messages": [], "total": 0}
        
        # Get chat history for this user only
        chat_history = user.get("chat_history", [])
        
        # Filter by chat_id if specified
        if chat_id != "default":
            chat_history = [msg for msg in chat_history if msg.get("chat_id") == chat_id]
        
        # Limit results
        chat_history = chat_history[-limit:] if len(chat_history) > limit else chat_history
        
        return {
            "messages": chat_history,
            "total": len(chat_history),
            "user_id": user_id,
            "chat_id": chat_id
        }
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat history"
        )

@router.post("/create")
async def create_chat(
    request: CreateChatRequest,
    current_user: User = Depends(get_verified_user)
):
    """Create a new chat session"""
    try:
        user_id = current_user.user_id
        chat_id = str(ObjectId())
        
        title = request.title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Create chat metadata
        chat_data = {
            "chat_id": chat_id,
            "title": SecurityUtils.sanitize_user_input(title, 100),
            "created_at": datetime.now(),
            "user_id": user_id,
            "message_count": 0
        }
        
        # Store chat metadata
        await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$push": {"chats": chat_data}},
            upsert=True
        )
        
        return {
            "chat_id": chat_id,
            "title": title,
            "created_at": chat_data["created_at"].isoformat(),
            "message": "Chat created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat"
        )

@router.get("/chats")
async def get_user_chats(current_user: User = Depends(get_verified_user)):
    """Get all user's chat sessions"""
    try:
        user_id = current_user.user_id
        
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return {"chats": [], "total": 0}
        
        chats = user.get("chats", [])
        
        return {
            "chats": chats,
            "total": len(chats),
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error getting user chats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chats"
        )

@router.delete("/chat/{chat_id}")
async def delete_chat(
    chat_id: str,
    current_user: User = Depends(get_verified_user)
):
    """Delete a specific chat session"""
    try:
        user_id = current_user.user_id
        
        # Remove chat from user's chats
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {"chats": {"chat_id": chat_id}}}
        )
        
        # Remove chat messages from history
        await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {"chat_history": {"chat_id": chat_id}}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        return {"message": "Chat deleted successfully", "chat_id": chat_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat"
        )

@router.get("/memory-summary")
async def get_memory_summary(current_user: User = Depends(get_verified_user)):
    """Get user's memory summary"""
    try:
        user_id = current_user.user_id
        user_email = current_user.email
        
        # Get user document
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return {
                "total_messages": 0,
                "total_chats": 0,
                "preferences": {},
                "interests": [],
                "hobbies": []
            }
        
        # Count messages
        total_messages = len(user.get("chat_history", []))
        total_chats = len(user.get("chats", []))
        
        # Get memory stats from vector/graph
        memory_stats = {
            "total_messages": total_messages,
            "total_chats": total_chats,
            "preferences": {
                "response_style": user.get("responseStyle", "neutral"),
                "role": user.get("role", "user")
            },
            "interests": user.get("interests", []),
            "hobbies": user.get("hobby", []),
            "last_activity": user.get("last_activity", user.get("createdAt", datetime.now())).isoformat() if isinstance(user.get("last_activity", user.get("createdAt")), datetime) else str(user.get("last_activity", "N/A")),
            "user_email": user_email
        }
        
        logger.info(f"Memory summary retrieved for user {user_id}")
        return memory_stats
        
    except Exception as e:
        logger.error(f"Error getting memory summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get memory summary"
        )

@router.post("/clear-memory")
async def clear_memory(current_user: User = Depends(get_verified_user)):
    """Clear user's chat memory (with confirmation)"""
    try:
        user_id = current_user.user_id
        
        # Clear chat history but keep profile
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "chat_history": [],
                    "chats": [],
                    "last_memory_clear": datetime.now()
                }
            }
        )
        
        logger.info(f"Memory cleared for user {user_id}")
        
        return {
            "message": "Memory cleared successfully",
            "cleared_at": datetime.now().isoformat(),
async def get_llm_response(prompt: str, user_id: str = "unknown") -> str:
    """Enhanced LLM response using the energetic, personalized main brain system"""
    return await main_brain_generate_response(
        user_id=user_id,
        message=prompt,
        search_results=None,
        image_url=None
    )

# Standard chat endpoint (for frontend compatibility)
class SendChatRequest(BaseModel):
    message: str
    user_email: str

@router.post("/send")
async def send_chat(request: SendChatRequest):
    """
    🎯 FRONTEND-COMPATIBLE CHAT ENDPOINT
    
    This endpoint provides compatibility with the frontend's sendChat() function
    while using the comprehensive memory management system underneath.
    """
    try:
        print(f"🎯 Frontend chat request from: {request.user_email}")
        print(f"📝 Message: {request.message}")
        
        # 🔍 DATABASE-FIRST ARCHITECTURE: Check if user exists (DO NOT auto-create)
        user = await users_collection.find_one({"email": request.user_email})
        if not user:
            # 🚨 CRITICAL: User does not exist - return error instead of auto-creating
            print(f"⛔ User {request.user_email} not found in MongoDB - rejecting chat")
            return {
                "reply": "I don't have any information about you yet. Please create an account or make sure you're properly logged in first.",
                "intent": "user_not_found",
                "success": False,
                "error": "User does not exist in database",
                "action_required": "Please create an account or login first"
            }
        
        user_id = str(user.get("_id", user.get("email", "unknown")))
        print(f"✅ User verified in MongoDB: {request.user_email}")
        
        # Load user memory using our comprehensive system
        print("📚 Loading user memory...")
        user_memory = await memory_manager.load_user_memory(user_id)
        
        # Build memory context
        memory_context = memory_manager.build_context_for_model(user_memory)
        
        # Get enhanced AI response using the new energetic main brain system
        # The main brain will handle all memory, context, and personalization automatically
        ai_response = await get_llm_response(request.message, user_id)
        
        # Process any memory updates
        if "[MEMORY_UPDATE]" in ai_response:
            try:
                # 1. Extract Thinking Data (if present) before splitting
                # main_brain appends it at the very end
                thinking_data_match = re.search(r"<!--THINKING_DATA:.*?-->", ai_response, re.DOTALL)
                thinking_data_block = thinking_data_match.group(0) if thinking_data_match else ""

                # 2. Process Memory Update (Standard logic)
                await memory_manager.process_memory_update_instructions(user_id, ai_response)
                print("✅ Memory updates processed successfully")
                
                # 3. Clean the response (removes everything after [MEMORY_UPDATE])
                ai_response = ai_response.split("[MEMORY_UPDATE]")[0].strip()
                
                # 4. Re-append Thinking Data if it was found and not already present (it was likely removed by split)
                if thinking_data_block and thinking_data_block not in ai_response:
                    ai_response += "\n\n" + thinking_data_block
                    
            except Exception as e:
                print(f"⚠️ Memory update failed: {e}")
        
        return {
            "reply": ai_response,
            "intent": "memory_enhanced_chat",
            "success": True,
            "debug_info": {
                "user_id": user_id,
                "memory_loaded": len(memory_context) > 0
            }
        }
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return {
            "reply": "I apologize, but I encountered an error processing your request. Please try again.",
            "intent": "error",
            "success": False,
            "error": str(e)
        }

# Memory-enhanced chat endpoint
@router.post("/memory-chat")
async def memory_enhanced_chat(request: SendMessageRequest):
    """
    🧠 MEMORY-ENHANCED CHAT ENDPOINT
    
    This endpoint demonstrates the memory system functionality:
    1. Loads user memory from all databases
    2. Injects memory context into AI prompt
    3. Processes memory updates from AI response
    4. Saves conversation for future reference
    """
    try:
        user_id = request.userId
        session_id = request.sessionId
        user_message = request.message
        
        print(f"🧠 Processing memory-enhanced chat for user: {user_id}")
        
        # Step 1: Load ALL user memory
        print("📚 Loading user memory...")
        user_memory = await memory_manager.load_user_memory(user_id)
        
        # Step 2: Build context for AI
        memory_context = memory_manager.build_context_for_model(user_memory)
        print(f"📄 Memory context built (length: {len(memory_context)})")
        
        # Step 3: Create enhanced prompt
        enhanced_prompt = f"""
=== USER MEMORY CONTEXT ===
{memory_context}

=== CURRENT MESSAGE ===
User: {user_message}

=== INSTRUCTIONS ===
- Use the memory context to provide personalized responses
- If user asks "what do you know about me", use the memory context
- If you learn something important, generate memory update instructions
- Be natural and conversational

Respond naturally based on the user's memory and context:
"""
        
        # Step 4: Get AI response
        print("🤖 Getting AI response...")
        ai_response = await get_llm_response(enhanced_prompt)
        
        # Step 5: Extract memory updates if present
        memory_updates = {}
        # Step 5: Extract memory updates if present
        memory_updates = {}
        if "[MEMORY_UPDATE]" in ai_response:
            try:
                # 1. Extract Thinking Data (if present) before splitting
                thinking_data_match = re.search(r"<!--THINKING_DATA:.*?-->", ai_response, re.DOTALL)
                thinking_data_block = thinking_data_match.group(0) if thinking_data_match else ""

                parts = ai_response.split("[MEMORY_UPDATE]")
                clean_response = parts[0].strip()
                memory_instruction_text = parts[1].split("[/MEMORY_UPDATE]")[0].strip()
                memory_updates = json.loads(memory_instruction_text)
                
                # Re-append thinking data to the clean response
                ai_response = clean_response
                if thinking_data_block and thinking_data_block not in ai_response:
                    ai_response += "\n\n" + thinking_data_block
                
                print(f"📝 Memory updates extracted: {list(memory_updates.keys())}")
            except Exception as e:
                print(f"⚠️ Error parsing memory updates: {e}")
        
        # Step 6: Process memory updates
        if memory_updates:
            print("💾 Processing memory updates...")
            update_results = await memory_manager.process_memory_update_instructions(user_id, memory_updates)
            print(f"✅ Memory updates processed: {update_results}")
        
        # Step 7: Save conversation
        await memory_manager.save_conversation(user_id, user_message, ai_response, memory_updates)
        print("💬 Conversation saved")
        
        return {
            "success": True,
            "response": ai_response,
            "sessionId": session_id,
            "debug": {
                "user_memory_loaded": bool(user_memory),
                "memory_context_length": len(memory_context),
                "memory_updates_applied": list(memory_updates.keys()) if memory_updates else [],
                "memory_stats": {
                    "profile": bool(user_memory.get('profile')),
                    "structured_memories": len(user_memory.get('structured_memory', [])),
                    "conversations": len(user_memory.get('conversations', [])),
                    "temp_memory": bool(user_memory.get('temp_memory')),
                    "graph_relationships": len(user_memory.get('graph_relationships', [])),
                }
            }
        }
        
    except Exception as e:
        print(f"❌ Memory-enhanced chat error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Memory processing failed: {str(e)}"
        }

# Memory testing endpoints
@router.get("/memory-test/{user_id}")
async def test_user_memory(user_id: str):
    """Test endpoint to check user memory loading"""
    try:
        print(f"🧪 Testing memory for user: {user_id}")
        
        # Load user memory
        user_memory = await memory_manager.load_user_memory(user_id)
        
        # Build context
        memory_context = memory_manager.build_context_for_model(user_memory)
        
        return {
            "success": True,
            "user_id": user_id,
            "memory_stats": {
                "profile_loaded": bool(user_memory.get('profile')),
                "structured_memories": len(user_memory.get('structured_memory', [])),
                "tasks": len(user_memory.get('tasks', [])),
                "conversations": len(user_memory.get('conversations', [])),
                "temp_memory": bool(user_memory.get('temp_memory')),
                "session_state": bool(user_memory.get('session_state')),
                "vector_memories": len(user_memory.get('vector_memories', [])),
                "graph_relationships": len(user_memory.get('graph_relationships', [])),
                "interests": len(user_memory.get('interests', []))
            },
            "context_preview": memory_context[:500] + "..." if len(memory_context) > 500 else memory_context
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Memory test failed: {str(e)}"
        }

@router.post("/memory-update/{user_id}")
async def manual_memory_update(user_id: str, updates: Dict[str, Any] = Body(...)):
    """Manual memory update endpoint for testing"""
    try:
        print(f"🛠️ Manual memory update for user: {user_id}")
        
        results = await memory_manager.process_memory_update_instructions(user_id, updates)
        
        return {
            "success": True,
            "user_id": user_id,
            "update_results": results,
            "instructions_processed": list(updates.keys())
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Manual memory update failed: {str(e)}"
        }

# Simple test endpoint
@router.get("/test")
async def test_endpoint():
    """Simple test to verify router is working"""
    return {
        "status": "Memory-enhanced chat router is working!",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "Memory loading from all databases",
            "Context injection into AI prompts", 
            "Memory update processing",
            "Conversation saving",
            "User validation and access control"
        ]
    }

# Create a separate users router for user profile endpoints
users_router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@users_router.get("/profile")
async def get_user_profile(email: str):
    """Get user profile by email"""
    try:
        print(f"📋 Fetching user profile for: {email}")
        
        # Find user in MongoDB
        user = await users_collection.find_one({"email": email})
        
        if not user:
            # Return default profile structure if user doesn't exist
            return {
                "email": email,
                "name": email.split("@")[0],
                "username": None,
                "hobby": [],
                "role": None,
                "interests": [],
                "responseStyle": None,
                "profilePicUrl": None,
                "createdAt": datetime.utcnow().isoformat()
            }
        
        # Convert MongoDB document to API response
        profile = {
            "email": user.get("email", email),
            "name": user.get("name", email.split("@")[0]),
            "username": user.get("username"),
            "hobby": user.get("hobby", []),
            "role": user.get("role"),
            "interests": user.get("interests", []),
            "responseStyle": user.get("responseStyle"),
            "profilePicUrl": user.get("profilePicUrl"),
            "createdAt": user.get("createdAt", datetime.utcnow()).isoformat() if isinstance(user.get("createdAt"), datetime) else user.get("createdAt")
        }
        
        print(f"✅ Profile found for {email}")
        return profile
        
    except Exception as e:
        print(f"❌ Error fetching profile for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user profile: {str(e)}")

class UpdateProfileRequest(BaseModel):
    email: str
    username: str = None
    hobby: list = []
    role: str = None
    interests: list = []
    responseStyle: str = None
    profilePicUrl: str = None

@users_router.put("/profile")
async def update_user_profile(request: UpdateProfileRequest):
    """Update user profile"""
    try:
        print(f"📝 Updating user profile for: {request.email}")
        
        # Build update document
        update_data = {
            "email": request.email,
            "updatedAt": datetime.utcnow()
        }
        
        if request.username is not None:
            update_data["username"] = request.username
        if request.hobby:
            update_data["hobby"] = request.hobby
        if request.role is not None:
            update_data["role"] = request.role
        if request.interests:
            update_data["interests"] = request.interests
        if request.responseStyle is not None:
            update_data["responseStyle"] = request.responseStyle
        if request.profilePicUrl is not None:
            update_data["profilePicUrl"] = request.profilePicUrl
        
        # Update or insert user
        result = await users_collection.update_one(
            {"email": request.email},
            {"$set": update_data},
            upsert=True
        )
        
        print(f"✅ Profile updated for {request.email}")
        return {
            "success": True,
            "message": "Profile updated successfully",
            "modified_count": result.modified_count,
            "upserted": result.upserted_id is not None
        }
        
    except Exception as e:
        print(f"❌ Error updating profile for {request.email}: {e}")
                "user_memory_loaded": bool(user_memory),
                "memory_context_length": len(memory_context),
                "memory_updates_applied": list(memory_updates.keys()) if memory_updates else [],
                "memory_stats": {
                    "profile": bool(user_memory.get('profile')),
                    "structured_memories": len(user_memory.get('structured_memory', [])),
                    "conversations": len(user_memory.get('conversations', [])),
                    "temp_memory": bool(user_memory.get('temp_memory')),
                    "graph_relationships": len(user_memory.get('graph_relationships', [])),
                }
            }
        }
        
    except Exception as e:
        print(f"❌ Memory-enhanced chat error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Memory processing failed: {str(e)}"
        }

# Memory testing endpoints
@router.get("/memory-test/{user_id}")
async def test_user_memory(user_id: str):
    """Test endpoint to check user memory loading"""
    try:
        print(f"🧪 Testing memory for user: {user_id}")
        
        # Load user memory
        user_memory = await memory_manager.load_user_memory(user_id)
        
        # Build context
        memory_context = memory_manager.build_context_for_model(user_memory)
        
        return {
            "success": True,
            "user_id": user_id,
            "memory_stats": {
                "profile_loaded": bool(user_memory.get('profile')),
                "structured_memories": len(user_memory.get('structured_memory', [])),
                "tasks": len(user_memory.get('tasks', [])),
                "conversations": len(user_memory.get('conversations', [])),
                "temp_memory": bool(user_memory.get('temp_memory')),
                "session_state": bool(user_memory.get('session_state')),
                "vector_memories": len(user_memory.get('vector_memories', [])),
                "graph_relationships": len(user_memory.get('graph_relationships', [])),
                "interests": len(user_memory.get('interests', []))
            },
            "context_preview": memory_context[:500] + "..." if len(memory_context) > 500 else memory_context
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Memory test failed: {str(e)}"
        }

@router.post("/memory-update/{user_id}")
async def manual_memory_update(user_id: str, updates: Dict[str, Any] = Body(...)):
    """Manual memory update endpoint for testing"""
    try:
        print(f"🛠️ Manual memory update for user: {user_id}")
        
        results = await memory_manager.process_memory_update_instructions(user_id, updates)
        
        return {
            "success": True,
            "user_id": user_id,
            "update_results": results,
            "instructions_processed": list(updates.keys())
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Manual memory update failed: {str(e)}"
        }

# Simple test endpoint
@router.get("/test")
async def test_endpoint():
    """Simple test to verify router is working"""
    return {
        "status": "Memory-enhanced chat router is working!",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "Memory loading from all databases",
            "Context injection into AI prompts", 
            "Memory update processing",
            "Conversation saving",
            "User validation and access control"
        ]
    }

# Create a separate users router for user profile endpoints
users_router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@users_router.get("/profile")
async def get_user_profile(email: str):
    """Get user profile by email"""
    try:
        print(f"📋 Fetching user profile for: {email}")
        
        # Find user in MongoDB
        user = await users_collection.find_one({"email": email})
        
        if not user:
            # Return default profile structure if user doesn't exist
            return {
                "email": email,
                "name": email.split("@")[0],
                "username": None,
                "hobby": [],
                "role": None,
                "interests": [],
                "responseStyle": None,
                "profilePicUrl": None,
                "createdAt": datetime.utcnow().isoformat()
            }
        
        # Convert MongoDB document to API response
        profile = {
            "email": user.get("email", email),
            "name": user.get("name", email.split("@")[0]),
            "username": user.get("username"),
            "hobby": user.get("hobby", []),
            "role": user.get("role"),
            "interests": user.get("interests", []),
            "responseStyle": user.get("responseStyle"),
            "profilePicUrl": user.get("profilePicUrl"),
            "createdAt": user.get("createdAt", datetime.utcnow()).isoformat() if isinstance(user.get("createdAt"), datetime) else user.get("createdAt")
        }
        
        print(f"✅ Profile found for {email}")
        return profile
        
    except Exception as e:
        print(f"❌ Error fetching profile for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user profile: {str(e)}")

class UpdateProfileRequest(BaseModel):
    email: str
    username: str = None
    hobby: list = []
    role: str = None
    interests: list = []
    responseStyle: str = None
    profilePicUrl: str = None

@users_router.put("/profile")
async def update_user_profile(request: UpdateProfileRequest):
    """Update user profile"""
    try:
        print(f"📝 Updating user profile for: {request.email}")
        
        # Build update document
        update_data = {
            "email": request.email,
            "updatedAt": datetime.utcnow()
        }
        
        if request.username is not None:
            update_data["username"] = request.username
        if request.hobby:
            update_data["hobby"] = request.hobby
        if request.role is not None:
            update_data["role"] = request.role
        if request.interests:
            update_data["interests"] = request.interests
        if request.responseStyle is not None:
            update_data["responseStyle"] = request.responseStyle
        if request.profilePicUrl is not None:
            update_data["profilePicUrl"] = request.profilePicUrl
        
        # Update or insert user
        result = await users_collection.update_one(
            {"email": request.email},
            {"$set": update_data},
            upsert=True
        )
        
        print(f"✅ Profile updated for {request.email}")
        return {
            "success": True,
            "message": "Profile updated successfully",
            "modified_count": result.modified_count,
            "upserted": result.upserted_id is not None
        }
        
    except Exception as e:
        print(f"❌ Error updating profile for {request.email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user profile: {str(e)}")

                "memory_updates_applied": list(memory_updates.keys()) if memory_updates else [],
                "memory_stats": {
                    "profile": bool(user_memory.get('profile')),
                    "structured_memories": len(user_memory.get('structured_memory', [])),
                    "conversations": len(user_memory.get('conversations', [])),
                    "temp_memory": bool(user_memory.get('temp_memory')),
                    "graph_relationships": len(user_memory.get('graph_relationships', [])),
                }
            }
        }
        
    except Exception as e:
        print(f"❌ Memory-enhanced chat error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"Memory processing failed: {str(e)}"
        }

# Memory testing endpoints
@router.get("/memory-test/{user_id}")
async def test_user_memory(user_id: str):
    """Test endpoint to check user memory loading"""
    try:
        print(f"🧪 Testing memory for user: {user_id}")
        
        # Load user memory
        user_memory = await memory_manager.load_user_memory(user_id)
        
        # Build context
        memory_context = memory_manager.build_context_for_model(user_memory)
        
        return {
            "success": True,
            "user_id": user_id,
            "memory_stats": {
                "profile_loaded": bool(user_memory.get('profile')),
                "structured_memories": len(user_memory.get('structured_memory', [])),
                "tasks": len(user_memory.get('tasks', [])),
                "conversations": len(user_memory.get('conversations', [])),
                "temp_memory": bool(user_memory.get('temp_memory')),
                "session_state": bool(user_memory.get('session_state')),
                "vector_memories": len(user_memory.get('vector_memories', [])),
                "graph_relationships": len(user_memory.get('graph_relationships', [])),
                "interests": len(user_memory.get('interests', []))
            },
            "context_preview": memory_context[:500] + "..." if len(memory_context) > 500 else memory_context
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Memory test failed: {str(e)}"
        }

@router.post("/memory-update/{user_id}")
async def manual_memory_update(user_id: str, updates: Dict[str, Any] = Body(...)):
    """Manual memory update endpoint for testing"""
    try:
        print(f"🛠️ Manual memory update for user: {user_id}")
        
        results = await memory_manager.process_memory_update_instructions(user_id, updates)
        
        return {
            "success": True,
            "user_id": user_id,
            "update_results": results,
            "instructions_processed": list(updates.keys())
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Manual memory update failed: {str(e)}"
        }

# Simple test endpoint
@router.get("/test")
async def test_endpoint():
    """Simple test to verify router is working"""
    return {
        "status": "Memory-enhanced chat router is working!",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "Memory loading from all databases",
            "Context injection into AI prompts", 
            "Memory update processing",
            "Conversation saving",
            "User validation and access control"
        ]
    }

# Create a separate users router for user profile endpoints
users_router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@users_router.get("/profile")
async def get_user_profile(email: str):
    """Get user profile by email"""
    try:
        print(f"📋 Fetching user profile for: {email}")
        
        # Find user in MongoDB
        user = await users_collection.find_one({"email": email})
        
        if not user:
            # Return default profile structure if user doesn't exist
            return {
                "email": email,
                "name": email.split("@")[0],
                "username": None,
                "hobby": [],
                "role": None,
                "interests": [],
                "responseStyle": None,
                "profilePicUrl": None,
                "createdAt": datetime.utcnow().isoformat()
            }
        
        # Convert MongoDB document to API response
        profile = {
            "email": user.get("email", email),
            "name": user.get("name", email.split("@")[0]),
            "username": user.get("username"),
            "hobby": user.get("hobby", []),
            "role": user.get("role"),
            "interests": user.get("interests", []),
            "responseStyle": user.get("responseStyle"),
            "profilePicUrl": user.get("profilePicUrl"),
            "createdAt": user.get("createdAt", datetime.utcnow()).isoformat() if isinstance(user.get("createdAt"), datetime) else user.get("createdAt")
        }
        
        print(f"✅ Profile found for {email}")
        return profile
        
    except Exception as e:
        print(f"❌ Error fetching profile for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user profile: {str(e)}")

class UpdateProfileRequest(BaseModel):
    email: str
    username: str = None
    hobby: list = []
    role: str = None
    interests: list = []
    responseStyle: str = None
    profilePicUrl: str = None

@users_router.put("/profile")
async def update_user_profile(request: UpdateProfileRequest):
    """Update user profile"""
    try:
        print(f"📝 Updating user profile for: {request.email}")
        
        # Build update document
        update_data = {
            "email": request.email,
            "updatedAt": datetime.utcnow()
        }
        
        if request.username is not None:
            update_data["username"] = request.username
        if request.hobby:
            update_data["hobby"] = request.hobby
        if request.role is not None:
            update_data["role"] = request.role
        if request.interests:
            update_data["interests"] = request.interests
        if request.responseStyle is not None:
            update_data["responseStyle"] = request.responseStyle
        if request.profilePicUrl is not None:
            update_data["profilePicUrl"] = request.profilePicUrl
        
        # Update or insert user
        result = await users_collection.update_one(
            {"email": request.email},
            {"$set": update_data},
            upsert=True
        )
        
        print(f"✅ Profile updated for {request.email}")
        return {
            "success": True,
            "message": "Profile updated successfully",
            "modified_count": result.modified_count,
            "upserted": result.upserted_id is not None
        }
        
    except Exception as e:
        print(f"❌ Error updating profile for {request.email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user profile: {str(e)}")

@users_router.get("/test")
async def test_users_endpoint():
    """Test endpoint for users router"""
    return {"status": "Users router is working!", "timestamp": datetime.now().isoformat()}

@router.post("/consolidate")
async def trigger_consolidation(current_user: User = Depends(get_verified_user)):
    """
    🧠 TRIGGER MEMORY CONSOLIDATION
    
    Manually triggers the 'Sleep on it' process:
    1. Analyzes recent conversations
    2. Extracts new facts
    3. Commits to long-term graph memory
    """
    try:
        from app.services.memory_consolidation_service import consolidation_service
        
        user_id = current_user.user_id
        result = await consolidation_service.consolidate_user_memory(user_id)
        
        return {
            "success": True,
            "message": "Memory consolidation complete",
            "stats": result
        }
    except Exception as e:
        logger.error(f"Consolidation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Consolidation failed: {str(e)}"
        )

# ============================================================================
# 🧠 MEMORY MANAGEMENT ENDPOINTS (Graph Visualization & Editing)
# ============================================================================

@router.get("/memory/graph")
async def get_memory_graph(current_user: User = Depends(get_verified_user)):
    """
    Get complete user knowledge graph for visualization.
    Returns nodes and links formatted for force-directed graphs.
    """
    try:
        user_id = current_user.user_id
        # ✅ Unified Architecture: Use Orchestrator
        graph_data = await unified_memory_orchestrator.get_knowledge_graph(user_id)
        
        return {
            "success": True,
            "data": graph_data,
            "stats": {
                "nodes": len(graph_data["nodes"]),
                "links": len(graph_data["links"])
            }
        }
    except Exception as e:
        logger.error(f"Error getting memory graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory graph: {str(e)}"
        )

class MemoryItemRequest(BaseModel):
    target: str
    relationship: str
    category: str = "Entity"

@router.post("/memory/relationship")
async def add_memory_relationship(
    request: MemoryItemRequest,
    current_user: User = Depends(get_verified_user)
):
    """
    Manually add a relationship to the knowledge graph.
    Example: User -[LIKES]-> "Quantum Computing"
    """
    try:
        user_id = current_user.user_id
        
        # ✅ Unified Architecture: Use Orchestrator
        result, logs = await unified_memory_orchestrator.store_memory(
            user_id=user_id,
            memory_content=(request.relationship, request.target),
            memory_type=MemoryType.RELATIONSHIP,
            metadata={"source": "manual_ui", "label": request.category}
        )
        
        if result.success:
            return {"success": True, "message": f"Added: {request.relationship} -> {request.target}"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed: {result.reason}")
            
    except Exception as e:
        logger.error(f"Error adding memory relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add relationship: {str(e)}"
        )

@router.delete("/memory/relationship")
async def delete_memory_relationship(
    request: MemoryItemRequest,
    current_user: User = Depends(get_verified_user)
):
    """
    Delete a specific relationship from the knowledge graph.
    """
    try:
        user_id = current_user.user_id
        
        # ✅ Unified Architecture: Use Orchestrator
        success = await unified_memory_orchestrator.delete_relationship(
            user_id=user_id,
            target=request.target,
            relationship_type=request.relationship
        )
        
        if success:
            return {"success": True, "message": f"Deleted: {request.relationship} -> {request.target}"}
        else:
            return {"success": False, "message": "Relationship not found or could not be deleted"}
            
    except Exception as e:
        logger.error(f"Error deleting memory relationship: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete relationship: {str(e)}"
        )

from app.services.behavior_engine import behavior_engine
import json

@router.post("/interaction_mode")
async def set_interaction_mode(
    request: dict = Body(...),
    current_user: User = Depends(get_verified_user)
):
    """
    Set a temporary interaction anchor (Mock API for now, real implementation would fetch from UI).
    Expected payload: {
        "relationship_style": "romantic" | "friend" | "professional",
        "assistant_nickname": "str",
        "user_nickname": "str",
        "emotional_mode": "str"
    }
    """
    try:
        user_id = current_user.user_id
        
        # Validate/Sanitize inputs
        anchor_data = {
            "relationship_style": request.get("relationship_style", "standard"),
            "assistant_nickname": request.get("assistant_nickname", "Prism"),
            "user_nickname": request.get("user_nickname", "User"),
            "emotional_mode": request.get("emotional_mode", "warm")
        }
        
        behavior_engine.set_interaction_anchor(user_id, anchor_data)
        
        return {"success": True, "message": "Interaction mode set", "mode": anchor_data}
    except Exception as e:
        logger.error(f"Error setting interaction mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/interaction_mode")
async def clear_interaction_mode(current_user: User = Depends(get_verified_user)):
    """Clear the current interaction anchor."""
    behavior_engine.clear_interaction_anchor(current_user.user_id)
    return {"success": True, "message": "returned to normal mode"}
