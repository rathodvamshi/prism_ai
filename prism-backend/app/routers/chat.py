"""
🎯 PERFECT CHAT API ROUTES

Using the exact architecture you specified:
- MongoDB for sessions and user data
- Redis for caching and temporary storage  
- Pinecone for vector memory
- Neo4j for relationship graphs
- Complete user separation guaranteed
"""

import logging
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from fastapi.responses import StreamingResponse
from app.models.chat_models import ChatRequest, ChatResponse
from app.models.perfect_models import SendMessageRequest, CreateUserRequest
# Temporarily commenting out to fix import errors
# from app.services.perfect_memory_pipeline import process_message, get_user_summary
from app.db.mongo_client import users_collection, sessions_collection, mini_agents_collection
from app.db.mongo_client import db

# Get highlights collection
highlights_collection = db.message_highlights
from app.services.advanced_memory_manager import memory_manager
from app.services import router_service
from app.services.cache_service import cache_service
from app.utils.llm_client import get_llm_response as groq_llm_response, get_llm_response_stream, generate_chat_title
from app.services.main_brain import generate_response as main_brain_generate_response
from pydantic import BaseModel, EmailStr
from app.routers.auth import User
from app.utils.auth import get_current_user_from_session
from app.utils.timeout_utils import tracked_timeout, TimeoutConfig
from app.utils.preprocess import preprocess as safe_preprocess
from app.cognitive.router_engine import route_message
from app.cognitive.context_stack import push_context, peek_context, pop_context
from app.db.mongo_client import tasks_collection
from app.services.task_service import create_task
from bson import ObjectId
from app.services.email_queue_service import remove_scheduled_email, schedule_task_reminder
logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)

# Helper function for memory-enhanced LLM calls
async def get_llm_response(prompt: str) -> str:
    """Simple LLM response function for memory-enhanced chat"""
    system_prompt = "You are a helpful AI assistant with access to user memory and context. Provide personalized, accurate responses based on the user's profile and history."
    return await groq_llm_response(prompt, system_prompt)
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid
import json
import logging
from bson import ObjectId
import asyncio

# Create a router specifically for chat
router = APIRouter(
    prefix="/chat",
    tags=["Perfect Chat System"]
)

class NewChatRequest(BaseModel):
    title: Optional[str] = None

class MessageRequest(BaseModel):
    chatId: str  # Changed from chat_id
    message: str

@router.post("/new", status_code=201)
async def create_new_chat(
    request: NewChatRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Creates a new chat session for the authenticated user.
    🟢 MongoDB is the single source of truth - session stored immediately.
    """
    try:
        session_id = str(uuid.uuid4())
        user_id = ObjectId(current_user.user_id)
        print(f"🆕 Creating new session: {session_id} for user: {user_id}")

        new_session = {
            "chat_id": session_id,
            "sessionId": session_id,  # Also store as sessionId for compatibility
            "user_id": user_id,
            "userId": user_id,  # Also store as userId for compatibility
            "title": request.title or "New Chat",
            "messages": [],
            "isPinned": False,
            "isSaved": False,
            "isDeleted": False,
            "created_at": datetime.utcnow(),
            "createdAt": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }
        # Store session in MongoDB immediately - this is the single source of truth
        result = await sessions_collection.insert_one(new_session)
        
        if not result.inserted_id:
            print(f"❌ Failed to insert session {session_id} into MongoDB")
            raise HTTPException(status_code=500, detail="Failed to create chat session in database")
        
        print(f"✅ Session {session_id} stored in MongoDB with ID: {result.inserted_id}")
        
        # Return session data - frontend will use this to update local state
        # Serialize datetime properly for JSON response
        created_at = new_session["created_at"]
        if isinstance(created_at, datetime):
            created_at_str = created_at.isoformat()
        else:
            created_at_str = str(created_at)
        
        return {
            "chat_id": session_id,
            "title": new_session["title"],
            "isPinned": False,
            "isSaved": False,
            "created_at": created_at_str
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")

class RenameChatRequest(BaseModel):
    title: str

class PinChatRequest(BaseModel):
    isPinned: bool

class SaveChatRequest(BaseModel):
    isSaved: bool

@router.patch("/{chat_id}/title")
async def rename_chat_title(
    chat_id: str,
    request: RenameChatRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Renames a chat session.
    """
    try:
        user_id = ObjectId(current_user.user_id)
        # Find and update
        result = await sessions_collection.update_one(
            {
                "$or": [{"chat_id": chat_id}, {"sessionId": chat_id}],
                "user_id": user_id
            },
            {"$set": {"title": request.title, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count == 0 and result.matched_count == 0:
             raise HTTPException(status_code=404, detail="Chat not found or unauthorized")
             
        return {"status": "success", "title": request.title}
    except Exception as e:
        print(f"❌ Error renaming chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{chat_id}/pin")
async def pin_chat_session(
    chat_id: str,
    request: PinChatRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """Pins or Unpins a chat."""
    try:
        user_id = ObjectId(current_user.user_id)
        result = await sessions_collection.update_one(
            {
                "$or": [{"chat_id": chat_id}, {"sessionId": chat_id}],
                "user_id": user_id
            },
            {"$set": {"isPinned": request.isPinned, "updated_at": datetime.utcnow()}}
        )
        if result.matched_count == 0:
             raise HTTPException(status_code=404, detail="Chat not found")
        return {"status": "success", "isPinned": request.isPinned}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{chat_id}/save")
async def save_chat_session(
    chat_id: str,
    request: SaveChatRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """Saves or Unsaves a chat."""
    try:
        user_id = ObjectId(current_user.user_id)
        result = await sessions_collection.update_one(
            {
                "$or": [{"chat_id": chat_id}, {"sessionId": chat_id}],
                "user_id": user_id
            },
            {"$set": {"isSaved": request.isSaved, "updated_at": datetime.utcnow()}}
        )
        if result.matched_count == 0:
             raise HTTPException(status_code=404, detail="Chat not found")
        return {"status": "success", "isSaved": request.isSaved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- TASKS ENDPOINTS ---
class TaskConfirmRequest(BaseModel):
    description: str
    due_date: Optional[str] = None 

class TaskUpdateRequest(BaseModel):
    due_date: Optional[str] = None
    description: Optional[str] = None

@router.get("/tasks/{status}")
async def get_tasks(
    status: str,
    current_user: User = Depends(get_current_user_from_session)
):
    """Fetch tasks (pending or completed)."""
    try:
        user_id = str(current_user.user_id)
        
        query = {"userId": user_id}
        
        if status == "completed":
            query["status"] = "completed"
        elif status == "pending":
            query["status"] = {"$in": ["pending", "queued"]}
        
        cursor = tasks_collection.find(query).sort("created_at", -1).limit(50)
        
        tasks_list = []
        async for t in cursor:
            # Handle due_date serialization
            d = t.get("due_date")
            if isinstance(d, datetime): d = d.isoformat()
            
            # Map MongoDB doc to Frontend Task interface
            tasks_list.append({
                "task_id": str(t["_id"]),
                "description": t.get("description"),
                "due_date": d,
                "completed": t.get("status") == "completed",
                "created_at": t.get("created_at")
            })
        return tasks_list
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        return []

@router.post("/tasks/confirm")
async def confirm_task(
    request: TaskConfirmRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """Create a new task."""
    try:
        user_id = str(current_user.user_id)
        due_date_obj = None
        if request.due_date:
            try:
                # Basic ISO parsing
                due_date_obj = datetime.fromisoformat(request.due_date.replace('Z', '+00:00'))
            except:
                due_date_obj = datetime.utcnow()

        new_task = {
            "userId": user_id,
            "description": request.description,
            "due_date": due_date_obj,
            "status": "pending",
            "email_status": "queued",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        res = await tasks_collection.insert_one(new_task)
        
        return {
            "task_id": str(res.inserted_id),
            "description": new_task["description"],
            "due_date": new_task["due_date"].isoformat() if new_task["due_date"] else None,
            "confirmation_message": f"Reminder set: {new_task['description']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    try:
        user_id = ObjectId(current_user.user_id)
        from app.services.task_service import reschedule_task
        
        # We only support rescheduling via this endpoint for now
        # Description updates could be added similarly
        if request.due_date:
            res = await reschedule_task(task_id, request.due_date, str(user_id))
            return {"success": True, "message": res["message"]}
            
        return {"success": False, "message": "No changes requested"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise HTTPException(status_code=500, detail="Failed to update task")

@router.delete("/tasks/{task_id}")
async def delete_task_endpoint(
    task_id: str,
    current_user: User = Depends(get_current_user_from_session)
):
    try:
        user_id = ObjectId(current_user.user_id)
        from app.services.task_service import cancel_task
        
        res = await cancel_task(task_id, str(user_id))
        return {"success": True, "message": res["message"]}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error terminating task: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete task")

# --- MINI AGENT ENDPOINTS ---
class CreateMiniAgentRequest(BaseModel):
    name: str = "New Agent"
    snippet: str

@router.get("/mini-agents")
async def get_mini_agents(current_user: User = Depends(get_current_user_from_session)):
    try:
        user_id = ObjectId(current_user.user_id)
        cursor = mini_agents_collection.find({"user_id": user_id}).sort("created_at", -1)
        agents = []
        async for a in cursor:
            agents.append({
                "id": str(a["_id"]),
                "name": a.get("name", "Mini Agent"),
                "snippet": a.get("snippet", ""),
                "messages": a.get("messages", []),
                "created_at": a.get("created_at")
            })
        return agents
    except Exception:
         return []

@router.post("/mini-agents")
async def create_mini_agent(
    request: CreateMiniAgentRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    user_id = ObjectId(current_user.user_id)
    new_agent = {
        "user_id": user_id,
        "name": request.name,
        "snippet": request.snippet,
        "messages": [],
        "created_at": datetime.utcnow()
    }
    res = await mini_agents_collection.insert_one(new_agent)
    return {
        "success": True, 
        "data": {
            "id": str(res.inserted_id),
            "name": new_agent["name"], 
            "snippet": new_agent["snippet"]
        }
    }

@router.delete("/mini-agents/{agent_id}")
async def delete_mini_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user_from_session)
):
    try:
        user_id = ObjectId(current_user.user_id)
        res = await mini_agents_collection.delete_one({"_id": ObjectId(agent_id), "user_id": user_id})
        return {"success": res.deleted_count > 0}
    except:
        return {"success": False}

@router.get("/chats")
async def get_user_chats(
    limit: int = 20, 
    skip: int = 0,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Retrieves all chat sessions for the authenticated user (Paginated).
    🟢 MongoDB is the single source of truth - returns all metadata from database.
    """
    try:
        user_id = ObjectId(current_user.user_id)
        # print(f"📥 Fetching chats for user: {user_id} (skip={skip}, limit={limit})")
        
        # Query: Filter by userId AND not deleted
        query = {
            "$or": [{"user_id": user_id}, {"userId": user_id}],
            "isDeleted": {"$ne": True}
        }
        
        # Use native MongoDB pagination for speed
        cursor = sessions_collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
    
        chats = []
        seen_ids = set()
        
        async for chat in cursor:
            chat_id = chat.get("chat_id") or chat.get("sessionId", "")
            
            if not chat_id or chat_id in seen_ids:
                continue
            
            seen_ids.add(chat_id)
            
            # Serialize datetime objects properly
            created_at = chat.get("created_at") or chat.get("createdAt")
            updated_at = chat.get("updated_at") or chat.get("updatedAt")
            
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()
            elif not created_at:
                created_at = datetime.utcnow().isoformat()

            if isinstance(updated_at, datetime):
                updated_at = updated_at.isoformat()
            elif not updated_at:
                updated_at = created_at
            
            chats.append({
                "chat_id": str(chat_id),
                "id": str(chat_id), # Add 'id' for compatibility
                "title": chat.get("title", "New Chat"),
                "isPinned": chat.get("isPinned", False),
                "isSaved": chat.get("isSaved", False),
                "created_at": str(created_at),
                "updated_at": str(updated_at),
                "createdAt": str(created_at), # Add camelCase for compatibility
                "updatedAt": str(updated_at),
                "message_count": len(chat.get("messages", [])),
            })
        
        return {"chats": chats}
    except Exception as e:
        print(f"❌ Error fetching chats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch chats: {str(e)}")

@router.get("/{chat_id}/history")
async def get_chat_history(
    chat_id: str,
    current_user: User = Depends(get_current_user_from_session),
):
    """
    Retrieves ALL message history for a specific chat session.
    🟢 Returns complete conversation - used when opening a session.
    """
    user_id = ObjectId(current_user.user_id)
    # Support both chat_id and sessionId field names
    session = await sessions_collection.find_one({
        "$and": [
            {"$or": [{"chat_id": chat_id}, {"sessionId": chat_id}]},
            {"$or": [{"user_id": user_id}, {"userId": user_id}]}
        ]
    })

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Return ALL messages (no limit) - full conversation history
    messages = session.get("messages", [])
    return {
        "messages": messages,
        "chat_id": chat_id,
        "title": session.get("title", "New Chat"),
        "message_count": len(messages)
    }

@router.get("/{chat_id}/data")
async def get_session_data(
    chat_id: str,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    ⚡ AGGREGATED SESSION DATALOADER
    Fetches Messages, Highlights, and Mini Agents in ONE parallel call.
    Drastically reduces frontend load time and network requests.
    """
    try:
        user_id = ObjectId(current_user.user_id)
        
        # Define collections
        # highlights_collection is already imported
        mini_agent_threads_coll = db.mini_agent_threads
        mini_agent_messages_coll = db.mini_agent_messages

        # Define tasks for parallel execution
        async def fetch_session():
            return await sessions_collection.find_one({
                "$and": [
                    {"$or": [{"chat_id": chat_id}, {"sessionId": chat_id}]},
                    {"$or": [{"user_id": user_id}, {"userId": user_id}]}
                ]
            })

        async def fetch_highlights():
            return await highlights_collection.find({
                "sessionId": chat_id,
            }, {"_id": 0}).to_list(length=None)

        async def fetch_mini_agent_threads():
            return await mini_agent_threads_coll.find({
                "sessionId": chat_id
            }, {"_id": 0}).to_list(length=None)

        # 🚀 Execute session, highlights, and threads fetch in parallel
        session, highlights, threads = await asyncio.gather(
            fetch_session(),
            fetch_highlights(),
            fetch_mini_agent_threads()
        )

        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # 🚀 Fetch Mini Agent Messages (Batch Optimisation)
        # Get all thread IDs
        thread_ids = [t.get("id") for t in threads if t.get("id")]
        
        mini_agent_messages = []
        if thread_ids:
            # Fetch all messages for these threads in one query
            mini_agent_messages = await mini_agent_messages_coll.find(
                {"threadId": {"$in": thread_ids}},
                {"_id": 0}
            ).sort("createdAt", 1).to_list(length=None)

        # Group messages by threadId
        messages_by_thread = {}
        for msg in mini_agent_messages:
            tid = msg.get("threadId")
            if tid not in messages_by_thread:
                messages_by_thread[tid] = []
            
            # Normalize message
            created_at = msg.get("createdAt")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            normalized_msg = {
                "id": msg.get("id", f"msg_{tid}_{len(messages_by_thread[tid])}"),
                "role": msg.get("role", msg.get("sender", "assistant")).replace("ai", "assistant"),
                "content": msg.get("content", msg.get("text", "")),
                "timestamp": created_at
            }
            if not normalized_msg["content"]: 
                normalized_msg["content"] = "[Content unavailable]"
                
            messages_by_thread[tid].append(normalized_msg)

        # Format Highlights
        formatted_highlights = []
        for h in highlights:
            created_at = h.get("createdAt")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            formatted_highlights.append({
                "highlightId": h.get("highlightId"),
                "messageId": h.get("messageId"),
                "text": h.get("text"),
                "color": h.get("color"),
                "startOffset": h.get("startIndex"),
                "endOffset": h.get("endIndex"),
                "note": h.get("note"),
                "createdAt": created_at
            })

        # Format Mini Agents (Attach messages)
        formatted_mini_agents = []
        for agent in threads:
            agent_id = agent.get("id")
            msgs = messages_by_thread.get(agent_id, [])
            created_at = agent.get("createdAt")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()
            
            formatted_mini_agents.append({
                "agentId": agent_id,
                "messageId": agent.get("messageId"),
                "selectedText": agent.get("selectedText"),
                "messages": msgs,
                "hasConversation": len(msgs) > 0,
                "createdAt": created_at,
                "sessionId": agent.get("sessionId")
            })

        # 🚀 EMBED HIGHLIGHTS INTO MESSAGES (Frontend Requirement)
        session_messages = session.get("messages", [])
        
        # Create a map of messageId -> highlights list
        highlights_by_message = {}
        for h in formatted_highlights:
            mid = h.get("messageId")
            if mid:
                if mid not in highlights_by_message:
                    highlights_by_message[mid] = []
                highlights_by_message[mid].append(h)
        
        # Attach highlights to messages
        for msg in session_messages:
            # Handle various ID fields (id, message_id)
            msg_id = msg.get("id") or msg.get("message_id")
            if msg_id and msg_id in highlights_by_message:
                msg["highlights"] = highlights_by_message[msg_id]
            else:
                msg["highlights"] = []

        # Serialize session timestamps
        session_updated = session.get("updated_at")
        if isinstance(session_updated, datetime):
            session_updated = session_updated.isoformat()

        return {
            "session": {
                "id": chat_id,
                "title": session.get("title", "New Chat"),
                "updated_at": session_updated,
                "isPinned": session.get("isPinned", False),
                "isSaved": session.get("isSaved", False)
            },
            "messages": session_messages, # Includes embedded highlights
            "highlights": formatted_highlights, # Kept for backward compatibility
            "miniAgents": formatted_mini_agents
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching session data: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch session data: {str(e)}")

@router.delete("/{chat_id}", status_code=200)
async def delete_chat(chat_id: str, current_user: User = Depends(get_current_user_from_session)):
    """
    Deletes a chat session PERFECTLY for the authenticated user.
    🟢 Hard delete from MongoDB - session must NOT come back after refresh.
    🟢 Handles both chat_id and sessionId field names.
    🟢 Verifies user ownership before deletion.
    """
    user_id = ObjectId(current_user.user_id)
    
    # First verify the session exists and belongs to user
    session = await sessions_collection.find_one({
        "$and": [
            {"$or": [{"chat_id": chat_id}, {"sessionId": chat_id}]},
            {"$or": [{"user_id": user_id}, {"userId": user_id}]}
        ]
    })
    
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Hard delete - remove completely from MongoDB
    result = await sessions_collection.delete_one({
        "$and": [
            {"$or": [{"chat_id": chat_id}, {"sessionId": chat_id}]},
            {"$or": [{"user_id": user_id}, {"userId": user_id}]}
        ]
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete chat session")

    return {"message": "Chat session deleted successfully", "deleted": True}



@router.put("/{chat_id}/rename")
async def rename_chat(
    chat_id: str,
    request: RenameChatRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Renames a chat session.
    🟢 Updates title in MongoDB - persists after refresh.
    """
    user_id = ObjectId(current_user.user_id)
    result = await sessions_collection.update_one(
        {
            "$and": [
                {"$or": [{"chat_id": chat_id}, {"sessionId": chat_id}]},
                {"$or": [{"user_id": user_id}, {"userId": user_id}]}
            ]
        },
        {
            "$set": {
                "title": request.title,
                "updated_at": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return {"message": "Chat renamed successfully", "title": request.title}

@router.put("/{chat_id}/pin")
async def pin_chat(
    chat_id: str,
    request: PinChatRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Pins or unpins a chat session.
    🟢 Updates isPinned in MongoDB - stays pinned after reload.
    """
    user_id = ObjectId(current_user.user_id)
    result = await sessions_collection.update_one(
        {
            "$and": [
                {"$or": [{"chat_id": chat_id}, {"sessionId": chat_id}]},
                {"$or": [{"user_id": user_id}, {"userId": user_id}]}
            ]
        },
        {
            "$set": {
                "isPinned": request.isPinned,
                "updated_at": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return {"message": "Chat pin status updated", "isPinned": request.isPinned}

@router.put("/{chat_id}/save")
async def save_chat(
    chat_id: str,
    request: SaveChatRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Saves or unsaves a chat session.
    🟢 Updates isSaved in MongoDB - appears in Saved section.
    """
    user_id = ObjectId(current_user.user_id)
    result = await sessions_collection.update_one(
        {
            "$and": [
                {"$or": [{"chat_id": chat_id}, {"sessionId": chat_id}]},
                {"$or": [{"user_id": user_id}, {"userId": user_id}]}
            ]
        },
        {
            "$set": {
                "isSaved": request.isSaved,
                "updated_at": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return {"message": "Chat save status updated", "isSaved": request.isSaved}

@router.post("/message")
async def send_message(
    request: MessageRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """Sends a message in a chat session and gets an AI response."""
    user_id = ObjectId(current_user.user_id)
    # Support both chat_id and sessionId field names
    # ⏱️ FAIL FAST: 300ms timeout for MongoDB session lookup
    session = await tracked_timeout(
        sessions_collection.find_one({
            "$and": [
                {"$or": [{"chat_id": request.chatId}, {"sessionId": request.chatId}]},
                {"$or": [{"user_id": user_id}, {"userId": user_id}]}
            ]
        }),
        timeout_ms=TimeoutConfig.MONGODB_FIND,
        service_name="MongoDB FIND (session)",
        fallback=None
    )

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Preprocess (entity-safe, dual-text); keep raw in storage
    _pre = safe_preprocess(request.message)
    _raw_text = _pre["raw_text"]
    _working_text = _pre["working_text"]

    user_message = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": _raw_text,
        "timestamp": datetime.now(timezone.utc),
    }

    # Add user message to the session and update timestamp
    # ⏱️ FAIL FAST: 300ms timeout for MongoDB update
    update_time = datetime.now(timezone.utc)
    await tracked_timeout(
        sessions_collection.update_one(
            {"_id": session["_id"]},
            {
                "$push": {"messages": user_message},
                "$set": {
                    "updated_at": update_time,
                    "updatedAt": update_time  # Update both field names for compatibility
                }
            }
        ),
        timeout_ms=TimeoutConfig.MONGODB_UPDATE,
        service_name="MongoDB UPDATE (user message)",
        fallback=None
    )

    # Cognitive routing payload (for executor/LLM grounding)
    routing = await route_message(str(user_id), request.chatId, _raw_text)
    routing_payload = routing.payload

    # Get AI response using working text (safe-normalized)
    ai_response_content = await get_llm_response(_working_text)

    ai_message = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": ai_response_content,
        "timestamp": datetime.now(timezone.utc),
    }

    # Add AI message to the session and update timestamp
    # ⏱️ FAIL FAST: 300ms timeout for MongoDB update
    update_time = datetime.now(timezone.utc)
    await tracked_timeout(
        sessions_collection.update_one(
            {"_id": session["_id"]},
            {
                "$push": {"messages": ai_message},
                "$set": {
                    "updated_at": update_time,
                    "updatedAt": update_time  # Update both field names for compatibility
                }
            }
        ),
        timeout_ms=TimeoutConfig.MONGODB_UPDATE,
        service_name="MongoDB UPDATE (AI message)",
        fallback=None
    )

    return {"response": ai_response_content, "message_id": ai_message["id"], "timestamp": ai_message["timestamp"], "routing": routing_payload}

@router.post("/message/stream")
async def send_message_stream(
    request: MessageRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    🌊 STREAMING CHAT ENDPOINT
    Streams AI responses in real-time for instant feedback.
    
    Flow:
    1. Save user message to database
    2. Stream AI response chunk-by-chunk to frontend
    3. Save complete AI response to database after streaming completes
    """
    # #region agent log helper
    import json as _json
    import traceback
    try:
        log_data = {
            "sessionId": "debug-session",
            "runId": "run-debug-1",
            "hypothesisId": "ENTRY",
            "location": "chat.py:send_message_stream",
            "message": "endpoint_called",
            "data": {
                "message": request.message[:100] if request.message else None,
                "chatId": request.chatId if hasattr(request, 'chatId') else None,
                "user_id": str(current_user.user_id) if current_user else None
            },
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        }
        with open(r"c:\Users\vamsh\Source\3_1\project_ps2\prism\prism-ai-studio\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(_json.dumps(log_data) + "\n")
    except Exception as e:
        # Log to stderr so we can see if logging itself fails
        import sys
        print(f"DEBUG LOG ERROR: {e}", file=sys.stderr)
        print(f"TRACEBACK: {traceback.format_exc()}", file=sys.stderr)
    # #endregion
    
    user_id = ObjectId(current_user.user_id)
    
    # Find session
    # ⏱️ FAIL FAST: 300ms timeout for MongoDB session lookup
    session = await tracked_timeout(
        sessions_collection.find_one({
            "$and": [
                {"$or": [{"chat_id": request.chatId}, {"sessionId": request.chatId}]},
                {"$or": [{"user_id": user_id}, {"userId": user_id}]}
            ]
        }),
        timeout_ms=TimeoutConfig.MONGODB_FIND,
        service_name="MongoDB FIND (session stream)",
        fallback=None
    )

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # ✅ STEP 1: Save user message to database
    logger.info(f"✅ [Step] User message received for user: {user_id}")
    logger.info(f"✅ [Step] Raw user input: {request.message[:100]}...")

    # Preprocess once; raw stored, working used for intent/LLM
    _pre = safe_preprocess(request.message)
    _raw_text = _pre["raw_text"]
    _working_text = _pre["working_text"]
    
    user_message = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "content": _raw_text,
        "timestamp": datetime.utcnow(),
    }

    # ⏱️ FAIL FAST: 300ms timeout for MongoDB update
    update_time = datetime.utcnow()
    await tracked_timeout(
        sessions_collection.update_one(
            {"_id": session["_id"]},
            {
                "$push": {"messages": user_message},
                "$set": {
                    "updated_at": update_time,
                    "updatedAt": update_time
                }
            }
        ),
        timeout_ms=TimeoutConfig.MONGODB_UPDATE,
        service_name="MongoDB UPDATE (user message stream)",
        fallback=None
    )
    logger.info(f"✅ [Step] User message persisted to MongoDB")
    
    # ✅ STEP 1.5: Save user message to Redis history for recall (CRITICAL)
    try:
        from app.db.redis_client import add_message_to_history
        await add_message_to_history(str(user_id), "user", _raw_text)
        logger.info(f"✅ [Step] User message saved to Redis history")
    except Exception as e:
        logger.warning(f"⚠️ Failed to save user message to Redis history: {e}")

    # ✅ STEP 2: DETECT INTENT - Load only required services
    logger.info(f"✅ [Step] Intent detection started")
    from app.services.intent_detector import load_services_for_message, ServiceIntent
    services = await load_services_for_message(_working_text)
    detected_intent = services["intent"]
    
    print(f"⚡ Intent detected: {detected_intent.value}")
    print(f"⚡ Services loaded: {[k for k in services.keys() if k != 'intent']}")
    logger.info(f"✅ [Step] Intent detected: {detected_intent.value}")
    logger.info(f"✅ [Step] Services loaded: {[k for k in services.keys() if k != 'intent']}")
    
    # Look at recent history so short follow-ups like "At 5 PM" can reuse context
    previous_ai_message = None
    try:
        history = session.get("messages", [])
        for msg in reversed(history):
            role = (msg.get("role") or "").lower()
            if role in ("assistant", "system", "ai"):
                previous_ai_message = (
                    msg.get("content")
                    or msg.get("message")
                    or msg.get("text")
                )
                if previous_ai_message:
                    break
    except Exception:
        previous_ai_message = None

    # Route the request before streaming any tokens
    routing = await route_message(str(user_id), request.chatId, _raw_text)
    routing_payload = routing.payload
    # ⚡ OPTIMIZATION: Skip heavy processing for casual chat
    # ⚠️ CRITICAL: Recall questions MUST bypass fast path and use main brain
    msg_lower = (_working_text or "").lower().strip()
    # Normalize common abbreviations and variations
    msg_normalized = msg_lower.replace(" u ", " you ").replace(" u,", " you,").replace(" u.", " you.")
    msg_normalized = msg_normalized.replace("what do u", "what do you").replace("what u", "what you")
    msg_normalized = msg_normalized.replace("what'd", "what did").replace("what's", "what is")
    msg_normalized = msg_normalized.replace(" u know", " you know").replace(" u remember", " you remember")
    
    # Comprehensive recall question patterns
    recall_patterns = [
        "what did we", "what we have", "what we discussed", "what we talked", "what we disscuddes",
        "which movies", "what movies", "what do you know", "what do you remember",
        "what did i just tell", "what did i just say", "what i just told", "what i just said",
        "what do you remember about", "what are my preferences", "tell me about myself",
        "what do you know about me", "what do you know about my", "what you know about me",
        "what do you remember about me", "what do you remember about my",
        "what did i tell you", "what did i say to you", "what i told you", "what i said to you",
        "what have i told", "what have i said", "what i've told", "what i've said",
        "what do u know", "what u know", "what do u know about me", "what u know about me",
        "what do u remember", "what u remember", "what do u remember about me",
        "tell me what you know", "tell me what you remember", "tell me about me",
        "what information do you have", "what info do you have", "what data do you have",
        "what can you tell me about", "what can you recall about", "what can you remember about"
    ]
    
    # Check patterns in both normalized and original message
    pattern_match = any(kw in msg_normalized for kw in recall_patterns) or any(kw in msg_lower for kw in recall_patterns)
    
    # Additional pattern matching for "what do you know about me" variations
    know_about_pattern = (
        "what" in msg_lower and 
        ("know" in msg_lower or "remember" in msg_lower) and 
        ("about" in msg_lower or "me" in msg_lower or "my" in msg_lower) and
        not any(exclude in msg_lower for exclude in ["how to", "how do", "how can", "how should"])
    )
    
    is_recall_question = (
        pattern_match or
        "recall" in msg_lower or
        know_about_pattern
    )
    
    if is_recall_question:
        logger.info(f"✅ [Step] Recall question detected: '{request.message[:50]}...' - bypassing fast path")
        logger.info(f"✅ [Step] Pattern match: {pattern_match}, Know about pattern: {know_about_pattern}")
    
    if detected_intent == ServiceIntent.CASUAL_CHAT and not is_recall_question:
        # Fast path for casual chat - minimal context (but NOT for recall questions)
        print("⚡ Fast path: Casual chat (Redis only)")
        router_result = {
            "intent": "casual_chat",
            "context": "",
            "action_payload": None,
            "direct_reply": None
        }
    else:
        # Full routing for complex intents OR recall questions
        if is_recall_question:
            logger.info(f"✅ [Step] Recall question detected - bypassing fast path")
        router_result = await router_service.process_request(
            message=_working_text,
            user_id=str(user_id),
            user_email=current_user.email,
            previous_ai_message=previous_ai_message,
            session_id=request.chatId,
        )

    # Prepare context and action payload for downstream use
    context_for_prompt = router_result.get("context") or ""
    action_payload = router_result.get("action_payload")
    direct_reply = router_result.get("direct_reply")
    intent = router_result.get("intent", "general_chat")
    
    # ⚠️ CRITICAL: Force recall questions to use main brain, override intent if needed
    if is_recall_question and intent == "casual_chat":
        logger.info(f"✅ [Step] Overriding intent from 'casual_chat' to 'recall_memory' for recall question")
        intent = "recall_memory"
    # Keep context bounded to avoid overly large prompts
    if len(context_for_prompt) > 4000:
        context_for_prompt = context_for_prompt[:4000]

    # Generate message ID for AI response
    ai_message_id = str(uuid.uuid4())
    ai_timestamp = datetime.utcnow()
    
    # Stream generator function
    async def generate_stream():
        """Generates SSE-formatted stream of AI response chunks"""
        nonlocal intent  # Allow modification of outer scope variable
        full_response = ""
        
        try:
            # Send initial metadata (SSE event: start)
            import json
            start_payload = {
                "message_id": ai_message_id,
                "timestamp": ai_timestamp.isoformat(),
                "intent": intent,
            }
            yield f"event: start\ndata: {json.dumps(start_payload)}\n\n"

            # Emit explicit action event for frontend rich rendering
            if action_payload:
                yield (
                    "event: action\n"
                    f"data: {json.dumps(action_payload)}\n\n"
                )

            # For long-running intents, send intermediate status updates
            if intent == "deep_research":
                # Step 1: indicate web search is starting
                status_search = {"step": "searching_web", "message": "Browsing the web..."}
                yield f"event: status\ndata: {json.dumps(status_search)}\n\n"
                # Step 2: indicate review/analysis phase
                status_reviews = {"step": "reading_reviews", "message": "Reading reviews..."}
                yield f"event: status\ndata: {json.dumps(status_reviews)}\n\n"

            # Handle pending confirmation/clarification from context stack
            msg_clean = (_raw_text or "").strip().lower()
            pending = await peek_context(str(user_id), request.chatId)
            if pending and isinstance(pending, dict):
                if pending.get("type") == "pending_action" and msg_clean in {"yes", "confirm", "okay", "ok"}:
                    act_intent = pending.get("intent")
                    act_entities = pending.get("entities", {})
                    # Execute supported actions
                    if act_intent == "task_cancel" and act_entities.get("task_id"):
                        tid = act_entities["task_id"]
                        try:
                            obj_id = ObjectId(tid)
                        except Exception:
                            obj_id = tid
                        await tasks_collection.update_one(
                            {"_id": obj_id, "userId": str(user_id)},
                            {"$set": {"status": "canceled", "updated_at": datetime.utcnow()}}
                        )
                        try:
                            await remove_scheduled_email(str(obj_id))
                        except Exception:
                            pass
                        await pop_context(str(user_id), request.chatId)
                        confirm_msg = f"✅ Canceled the reminder: {act_entities.get('task_name') or tid}"
                        full_response = confirm_msg
                        yield f"event: token\ndata: {confirm_msg}\n\n"
                        usage = {"prompt": len(_working_text or ""), "completion": len(full_response)}
                        yield f"event: done\ndata: {json.dumps({'usage': usage})}\n\n"
                        return
                    elif act_intent == "task_update" and act_entities.get("task_id") and act_entities.get("new_time_iso"):
                        # Parse new time and validate
                        import datetime as _dt
                        try:
                            new_dt = _dt.datetime.fromisoformat(act_entities["new_time_iso"].replace("Z", "+00:00"))
                        except Exception:
                            new_dt = None
                        if not new_dt:
                            err = "❌ Could not parse the new time. Please specify a valid time."
                            yield f"event: token\ndata: {err}\n\n"
                            yield f"event: done\ndata: {json.dumps({'usage': {'prompt': len(_working_text or ''), 'completion': len(err)}})}\n\n"
                            return
                        # Reject past times
                        now_utc = _dt.datetime.now(_dt.timezone.utc)
                        if not new_dt.tzinfo:
                            new_dt = new_dt.replace(tzinfo=_dt.timezone.utc)
                        if new_dt < now_utc:
                            err = "⚠️ The new time is in the past. Update rejected."
                            yield f"event: token\ndata: {err}\n\n"
                            yield f"event: done\ndata: {json.dumps({'usage': {'prompt': len(_working_text or ''), 'completion': len(err)}})}\n\n"
                            return
                        # Convert to timezone-aware UTC for Mongo storage and reschedule email
                        aware_utc = new_dt.astimezone(_dt.timezone.utc)
                        tid = act_entities["task_id"]
                        try:
                            obj_id = ObjectId(tid)
                        except Exception:
                            obj_id = tid
                        await tasks_collection.update_one(
                            {"_id": obj_id, "userId": str(user_id)},
                            {"$set": {"due_date": aware_utc, "updated_at": _dt.datetime.now(_dt.timezone.utc)}}
                        )
                        # Reschedule email job: remove then add
                        try:
                            await remove_scheduled_email(str(obj_id))
                        except Exception:
                            pass
                        try:
                            await schedule_task_reminder(str(obj_id), str(user_id), new_dt.timestamp())
                        except Exception as e:
                            err = f"⚠️ Failed to reschedule email: {e}"
                            yield f"event: token\ndata: {err}\n\n"
                            yield f"event: done\ndata: {json.dumps({'usage': {'prompt': len(_working_text or ''), 'completion': len(err)}})}\n\n"
                            return
                        await pop_context(str(user_id), request.chatId)
                        done_msg = f"✅ Rescheduled '{act_entities.get('task_name') or tid}' to {act_entities.get('new_time_iso')}"
                        yield f"event: token\ndata: {done_msg}\n\n"
                        yield f"event: done\ndata: {json.dumps({'usage': {'prompt': len(_working_text or ''), 'completion': len(done_msg)}})}\n\n"
                        return

                    elif act_intent == "task_create":
                        # Validate
                        desc = act_entities.get("task_name") or act_entities.get("description")
                        d_iso = act_entities.get("target_time") or act_entities.get("due_date_iso")
                        
                        if not desc or not d_iso:
                            err = "❌ Missing task details (need description and time)."
                            yield f"event: token\ndata: {err}\n\n"
                            yield f"event: done\ndata: {json.dumps({'usage': {'prompt': 0, 'completion': 0}})}\n\n"
                            return

                        # Get user details for email
                        user_email_val = current_user.email if hasattr(current_user, 'email') else None
                        
                        try:
                            # Create using the service (handles DB + Email Queue)
                            res = await create_task(
                                user_id=str(user_id),
                                description=desc,
                                due_date_iso=d_iso,
                                user_email=user_email_val
                            )
                            
                            # Log and Notify
                            logger.info(f"✅ Task created via Chat confirmation: {desc} for {d_iso}")
                            
                            await pop_context(str(user_id), request.chatId)
                            
                            # Friendly message
                            time_str = ""
                            try:
                                import datetime as _dt
                                t_obj = _dt.datetime.fromisoformat(d_iso.replace("Z", "+00:00"))
                                # Convert to IST for display if possible, or just formatted
                                time_str = t_obj.strftime("%I:%M %p")
                            except:
                                time_str = "scheduled time"

                            confirm_msg = f"✅ Reminder set: {desc} at {time_str}"
                            yield f"event: token\ndata: {confirm_msg}\n\n"
                            
                            # Emit action to refresh tasks on frontend
                            action_payload = {
                                "type": "task_created",
                                "data": res.get("task")
                            }
                            yield f"event: action\ndata: {json.dumps(action_payload)}\n\n"

                            yield f"event: done\ndata: {json.dumps({'usage': {'prompt': 0, 'completion': len(confirm_msg)}})}\n\n"
                            return
                        except Exception as e:
                             logger.error(f"❌ Failed to create task via Chat: {e}")
                             
                             # Check if it's a daily limit error
                             error_str = str(e)
                             if "daily_limit_reached" in error_str:
                                 # Extract the formatted error message
                                 parts = error_str.split("|", 1)
                                 limit_message = parts[1] if len(parts) > 1 else "You've reached your daily limit of 3 tasks! 🎯"
                                 
                                 # Send limit message with upgrade suggestion
                                 yield f"event: token\ndata: {limit_message}\n\n"
                                 
                                 # Optional: Send action for upgrade modal
                                 upgrade_action = {
                                     "type": "daily_limit_reached",
                                     "data": {
                                         "message": limit_message,
                                         "limit": 3,
                                         "upgrade_url": "/pricing"  # Future: link to pricing page
                                     }
                                 }
                                 yield f"event: action\ndata: {json.dumps(upgrade_action)}\n\n"
                             else:
                                 # Generic error
                                 err = "❌ Sorry, I failed to save that task. Please try again."
                                 yield f"event: token\ndata: {err}\n\n"
                             
                             yield f"event: done\ndata: {json.dumps({'usage': {'prompt': 0, 'completion': 0}})}\n\n"
                             return
                        return
                elif pending.get("type") == "pending_action" and msg_clean in {"no", "cancel", "don't", "stop"}:
                    await pop_context(str(user_id), request.chatId)
                    # Use a minimal message so frontend can show the red failure text
                    cancel_msg = "❌ Task creation cancelled. When would you like to create it? Or do you want to change the date/time?"
                    yield f"event: token\ndata: {cancel_msg}\n\n"
                    # Also try to emit a cancellation event if the frontend supports it to update the card
                    yield f"event: action\ndata: {json.dumps({'type': 'task_cancelled'})}\n\n"
                    yield f"event: done\ndata: {json.dumps({'usage': {'prompt': 0, 'completion': len(cancel_msg)}})}\n\n"
                    return
                elif pending.get("type") == "pending_selection":
                    # Handle numeric selection (1..N) or description match
                    opts = pending.get("options", [])
                    chosen = None
                    if msg_clean.isdigit():
                        idx = int(msg_clean) - 1
                        if 0 <= idx < len(opts):
                            chosen = opts[idx]
                    else:
                        for o in opts:
                            desc = (o.get("description") or "").lower()
                            if desc and desc in msg_clean:
                                chosen = o
                                break
                    if chosen:
                        # Replace with pending_action
                        await pop_context(str(user_id), request.chatId)
                        await push_context(str(user_id), request.chatId, {
                            "type": "pending_action",
                            "intent": pending.get("intent"),
                            "entities": {"task_id": chosen.get("task_id"), "task_name": chosen.get("description"), "new_time_iso": pending.get("new_time_iso")},
                        })
                        # Emit confirmation request for the chosen item
                        # Build explicit change payload for updates if time is present
                        old_iso = None
                        try:
                            doc = await tasks_collection.find_one({
                                "_id": ObjectId(chosen.get("task_id")), "userId": str(user_id)
                            })
                        except Exception:
                            doc = None
                        if doc and doc.get("due_date"):
                            try:
                                od = doc["due_date"]
                                old_iso = od.strftime('%Y-%m-%dT%H:%M:%SZ')
                            except Exception:
                                old_iso = None
                        if pending.get("intent") == "task_update":
                            conf_payload = {
                                "type": "confirmation_request",
                                "intent": pending.get("intent"),
                                "message": f"Reschedule '{chosen.get('description')}' from {old_iso} to {pending.get('new_time_iso')}?",
                                "changes": {
                                    "field": "time",
                                    "old_value": old_iso,
                                    "new_value": pending.get("new_time_iso"),
                                },
                            }
                        else:
                            conf_payload = {
                                "type": "confirmation_request",
                                "intent": pending.get("intent"),
                                "message": f"I am about to {('delete' if pending.get('intent')=='task_cancel' else 'update')} the task '{chosen.get('description')}'. Confirm?",
                                "entities": {"task_id": chosen.get("task_id"), "task_name": chosen.get("description")},
                            }
                        yield f"event: confirmation\ndata: {json.dumps(conf_payload)}\n\n"
                        yield f"event: done\ndata: {json.dumps({'usage': {'prompt': len(_working_text or ''), 'completion': 0}})}\n\n"
                        return

            # If router produced clarification or confirmation directives, emit and exit
            if routing_payload.get("clarification"):
                pending_sel = {
                    "type": "pending_selection",
                    "intent": routing_payload.get("intent_packet", {}).get("primary_intent"),
                    "options": routing_payload["clarification"].get("options", []),
                    "new_time_iso": routing_payload.get("entities_resolved", {}).get("new_time_iso"),
                }
                await push_context(str(user_id), request.chatId, pending_sel)
                yield f"event: clarification\ndata: {json.dumps(routing_payload['clarification'])}\n\n"
                yield f"event: done\ndata: {json.dumps({'usage': {'prompt': len(_working_text or ''), 'completion': 0}})}\n\n"
                return
            if routing_payload.get("execution_directives", {}).get("requires_confirmation"):
                # Build and emit confirmation request for supported intents
                pi = routing_payload.get("intent_packet", {}).get("primary_intent")
                ents = routing_payload.get("entities_resolved", {})
                if pi in {"task_cancel", "task_update", "task_create"}:
                    verb = "delete" if pi == "task_cancel" else ("update" if pi == "task_update" else "create")
                    target = ents.get("task_name") or ents.get("description") or _raw_text[:80]
                    if pi == "task_update":
                        # Build explicit changes with old/new values if possible
                        old_iso = None
                        new_iso = ents.get("new_time_iso")
                        if ents.get("task_id"):
                            try:
                                doc = await tasks_collection.find_one({
                                    "_id": ObjectId(ents["task_id"]), "userId": str(user_id)
                                })
                            except Exception:
                                doc = None
                            if doc and doc.get("due_date"):
                                try:
                                    od = doc["due_date"]
                                    old_iso = od.strftime('%Y-%m-%dT%H:%M:%SZ')
                                except Exception:
                                    old_iso = None
                        msg_text = f"Reschedule '{target}'" + (f" from {old_iso} to {new_iso}?" if old_iso and new_iso else "?")
                        conf_payload = {
                            "type": "confirmation_request",
                            "intent": pi,
                            "message": msg_text,
                            "changes": {
                                "field": "time",
                                "old_value": old_iso,
                                "new_value": new_iso,
                            },
                        }
                    else:
                        conf_payload = {
                            "type": "confirmation_request",
                            "intent": pi,
                            "message": f"I am about to {verb} the task '{target}'. Confirm?",
                            "entities": ents,
                        }
                    await push_context(str(user_id), request.chatId, {"type": "pending_action", "intent": pi, "entities": ents})
                    yield f"event: confirmation\ndata: {json.dumps(conf_payload)}\n\n"
                    yield f"event: done\ndata: {json.dumps({'usage': {'prompt': len(_working_text or ''), 'completion': 0}})}\n\n"
                    return

            # If the router already produced a direct reply (e.g., task or email), stream that and exit
            if direct_reply is not None:
                full_response = str(direct_reply)
                yield f"data: {json.dumps({'type': 'chunk', 'content': full_response})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            else:
                # GENERAL CHAT: always route through the Main Brain so PRISM sees Redis + Neo4j + deep memory
                # ✅ STEP 3: Generate response (with memory context for recall questions)
                # Force recall questions to use main brain even if intent is casual_chat
                if intent == "general_chat" or intent == "recall_memory" or is_recall_question:
                    if is_recall_question:
                        logger.info(f"✅ [Step] Recall question - forcing Main Brain (bypassing fast path)")
                        intent = "recall_memory"  # Override intent for proper handling
                    logger.info(f"✅ [Step] Generating response via Main Brain (intent: {intent})")
                    logger.info(f"✅ [Step] Memory-aware pipeline active for recall questions")
                    
                    # Pass session_id to main_brain for conversation history fetching
                    session_id_for_brain = str(session.get("_id")) if session else request.chatId
                    
                    # Run Brain
                    brain_pending = asyncio.create_task(main_brain_generate_response(
                        user_id=str(user_id),
                        message=_working_text,
                        search_results=context_for_prompt or None,
                        image_url=None,
                        session_id=session_id_for_brain,
                    ))
                    
                    # Wait for brain response
                    full_response = await brain_pending
                    
                    # ⚡ AUTO-RENAME: Generate AFTER response for perfect naming
                    try:
                        current_title = session.get("title", "Untitled")
                        if current_title in ["New Chat", "Untitled", "", None]:
                            # Use BOTH user query and AI response for a truly "sweet" title
                            new_title = await generate_chat_title(request.message, full_response)
                            if new_title and new_title not in ["New Chat", "Untitled"]:
                                await sessions_collection.update_one(
                                     {"_id": session["_id"]},
                                     {"$set": {"title": new_title}}
                                )
                                yield f"event: title\ndata: {json.dumps({'title': new_title})}\n\n"
                                logger.info(f"✅ [Step] Auto-renamed chat to: {new_title}")
                    except Exception as e:
                        logger.warning(f"⚠️ Title generation failed: {e}")

                    logger.info(f"✅ [Step] Response generated (length: {len(full_response)})")
                    # Stream the full response as a single logical token
                    yield f"event: token\ndata: {full_response}\n\n"
                    usage = {
                        "prompt": len(_working_text or ""),
                        "completion": len(full_response),
                    }
                    
                    yield f"event: done\ndata: {json.dumps({'usage': usage})}\n\n"
                else:
                    # TOOL-ENHANCED FLOWS: use lightweight context + raw streaming
                    system_prompt = (
                        "You are a helpful AI assistant. Provide clear, concise responses. "
                        "Use the provided context (if any) before answering."
                    )
                    if context_for_prompt:
                        system_prompt += f"\n\nContext:\n{context_for_prompt}"

                    async for chunk in get_llm_response_stream(_working_text, system_prompt):
                        full_response += chunk
                        # Send token as SSE (raw text chunk)
                        yield f"event: token\ndata: {chunk}\n\n"

                    # ⚡ AUTO-RENAME: Generate AFTER response for perfect context
                    # if not title_task: # Removed check as title_task is separate
                    try:
                        current_title = session.get("title", "Untitled")
                        if current_title in ["New Chat", "Untitled", "", None]:
                            new_title = await generate_chat_title(request.message, full_response)
                            if new_title and new_title not in ["New Chat", "Untitled"]:
                                await sessions_collection.update_one(
                                        {"_id": session["_id"]},
                                        {"$set": {"title": new_title}}
                                )
                                yield f"event: title\ndata: {json.dumps({'title': new_title})}\n\n"
                    except Exception as e:
                        logger.warning(f"⚠️ Title generation failed: {e}") 

                    # Send completion signal with basic usage info
                    usage = {
                        "prompt": len(_working_text or ""),
                        "completion": len(full_response),
                    }

                    yield f"event: done\ndata: {json.dumps({'usage': usage})}\n\n"
            
            # ✅ STEP 4: Save complete AI message to database after streaming/direct reply
            logger.info(f"✅ [Step] Saving AI response to database")
            ai_message = {
                "id": ai_message_id,
                "role": "assistant",
                "content": full_response,
                "timestamp": ai_timestamp,
                "metadata": {
                    "intent": intent,
                    "action_payload": action_payload,
                    "routing": routing_payload,
                }
            }
            
            update_time = datetime.utcnow()
            await sessions_collection.update_one(
                {"_id": session["_id"]},
                {
                    "$push": {"messages": ai_message},
                    "$set": {
                        "updated_at": update_time,
                        "updatedAt": update_time
                    }
                }
            )
            logger.info(f"✅ [Step] AI response persisted to MongoDB")
            
            # ✅ STEP 4.5: Save to Redis history for recall (CRITICAL for conversation history)
            try:
                from app.db.redis_client import add_message_to_history
                await add_message_to_history(str(user_id), "user", _raw_text)
                await add_message_to_history(str(user_id), "assistant", full_response)
                logger.info(f"✅ [Step] Messages saved to Redis history for recall")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save to Redis history: {e}")
            
            # ✅ STEP 5: Extract and save user details (background task - raw-only extraction)
            # This runs in parallel after streaming completes - doesn't block response
            logger.info(f"✅ [Step] Starting background extraction task (raw user input only)")

            from app.services.user_detail_extractor import extract_and_save_user_details_async
            from app.services.cache_service import cache_service
            
            # Create a task that will check atomic save result for acknowledgement
            from app.services.user_detail_extractor import user_detail_extractor
            async def extraction_with_acknowledgement():
                try:
                    # Extract details from RAW user message ONLY
                    extracted = await user_detail_extractor.extract_user_details(
                        str(user_id),
                        _raw_text,
                        None  # STRICT: pass only raw user input
                    )
                    
                    # ✅ STEP 6: Save if extraction successful; acknowledge only if atomic save succeeds
                    if extracted.get("extracted"):
                        logger.info(f"✅ [Step] Extraction successful - starting atomic save")
                        save_results = await user_detail_extractor.save_extracted_details(
                            str(user_id),
                            extracted,
                            _raw_text
                        )
                        
                        # ✅ MEMORY ACKNOWLEDGEMENT GUARD: Only acknowledge if all stores succeed
                        if save_results.get("atomic_saved"):
                            logger.info(f"✅ [Ack] Memory stored atomically for user: {user_id}")
                            logger.info(f"✅ [Step] Memory acknowledgement: APPROVED (MongoDB + Neo4j + Vector all succeeded)")
                            logger.info(f"✅ [Step] Save results: MongoDB={save_results.get('mongodb')}, Neo4j={save_results.get('neo4j')}, Vector={save_results.get('vector')}")
                        else:
                            logger.warning(f"⚠️ [Ack] Memory NOT stored atomically for user: {user_id}")
                            logger.warning(f"❌ [Step] Memory acknowledgement: DENIED (atomic save failed)")
                            logger.warning(f"❌ [Step] Save results: MongoDB={save_results.get('mongodb')}, Neo4j={save_results.get('neo4j')}, Vector={save_results.get('vector')}")
                    else:
                        logger.info(f"✅ [Step] No extractable details found - no memory save needed")
                except Exception as e:
                    logger.error(f"❌ [Step] Extraction task error: {e}")
            
            # Fire and forget - runs in background
            asyncio.create_task(extraction_with_acknowledgement())
            print(f"🚀 Background task started: User detail extraction for user {user_id}")

            # ✅ STEP 7: Cache invalidation after user message + potential memory updates
            logger.info(f"✅ [Step] Invalidating cache after message persistence")
            try:
                session_id = str(session.get("_id")) if session else request.chatId
                if session_id:
                    await cache_service.invalidate_keys([
                        f"highlights:{session_id}",
                        f"miniagents:{session_id}",
                        f"history:{session_id}"
                    ])
                    logger.info("[Flow] Cache invalidated for session updates")
                    logger.info(f"✅ [Step] Cache invalidated for session: {session_id}")
            except Exception as e:
                logger.warning(f"[Cache] Invalidation error: {e}")
                logger.warning(f"❌ [Step] Cache invalidation failed: {e}")
            
        except Exception as e:
            print(f"❌ Streaming error: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
    
    # Return streaming response with SSE headers
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

# Test endpoint to verify memory manager works
@router.get("/test-memory")
async def test_memory_endpoint():
    """Simple test endpoint to verify memory manager is working"""
    try:
        return {"status": "Memory manager imported successfully", "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


@router.get("/debug-location/{user_id}")
async def debug_location_endpoint(user_id: str):
    """
    🔧 DEBUG ENDPOINT: Check location resolution for a user
    
    Tests:
    1. MongoDB profile lookup
    2. Location intelligence resolution
    3. Memory orchestrator holographic context
    """
    try:
        from bson import ObjectId
        from app.services.location_intelligence import location_intelligence, get_location_context
        from app.services.unified_memory_orchestrator import unified_memory_orchestrator
        
        debug_info = {
            "user_id": user_id,
            "tests": {}
        }
        
        # Test 1: Direct MongoDB lookup
        try:
            user = await users_collection.find_one(
                {"_id": ObjectId(user_id)},
                {"profile": 1, "name": 1, "email": 1}
            )
            debug_info["tests"]["mongodb_direct"] = {
                "found": user is not None,
                "profile": user.get("profile") if user else None,
                "name": user.get("name") if user else None
            }
        except Exception as e:
            debug_info["tests"]["mongodb_direct"] = {"error": str(e)}
        
        # Test 2: Location intelligence
        try:
            location_data = await location_intelligence.resolve_location(
                user_id, "test query near me", None
            )
            debug_info["tests"]["location_intelligence"] = location_data
        except Exception as e:
            debug_info["tests"]["location_intelligence"] = {"error": str(e)}
        
        # Test 3: Location context string
        try:
            context_str = await get_location_context(user_id, "temples near me", None)
            debug_info["tests"]["location_context_string"] = context_str
        except Exception as e:
            debug_info["tests"]["location_context_string"] = {"error": str(e)}
        
        # Test 4: Holographic context
        try:
            holo_context, logs = await unified_memory_orchestrator.get_holographic_context(
                user_id=user_id,
                query="temples near me",
                intent="general"
            )
            debug_info["tests"]["holographic_context"] = {
                "profile": holo_context.get("profile"),
                "logs": logs
            }
        except Exception as e:
            debug_info["tests"]["holographic_context"] = {"error": str(e)}
        
        # Test 5: Cache status
        try:
            cached = unified_memory_orchestrator._get_cached_profile(user_id)
            debug_info["tests"]["cache_status"] = {
                "cached": cached is not None,
                "cached_data": cached
            }
        except Exception as e:
            debug_info["tests"]["cache_status"] = {"error": str(e)}
        
        return debug_info
        
    except Exception as e:
        return {"error": str(e), "user_id": user_id}


@router.post("/clear-cache/{user_id}")
async def clear_cache_endpoint(user_id: str):
    """
    🗑️ Clear cache for a user to force fresh data fetch
    """
    try:
        from app.services.unified_memory_orchestrator import unified_memory_orchestrator
        from app.services.location_intelligence import location_intelligence
        
        # Clear orchestrator cache
        unified_memory_orchestrator.invalidate_cache(user_id)
        
        # Clear location intelligence cache
        if user_id in location_intelligence.location_cache:
            del location_intelligence.location_cache[user_id]
        
        return {"success": True, "message": f"Cache cleared for user {user_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Pydantic models for new endpoints
class ChatMessage(BaseModel):
    messageId: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: dict = {}

class ChatSession(BaseModel):
    sessionId: str
    user_id: str
    title: str = "New Conversation"
    messages: List[ChatMessage] = []
    createdAt: datetime
    updatedAt: datetime
    isActive: bool = True

class HighlightRequest(BaseModel):
    sessionId: str
    messageId: str
    text: str
    color: str
    startIndex: int
    endIndex: int

class MiniAgentRequest(BaseModel):
    sessionId: str
    messageId: str
    selectedText: str
    userPrompt: str

class ShareRequest(BaseModel):
    sessionId: str
    includeHighlights: bool = False

# 🚀 PERFECT CHAT ENDPOINT - EXACTLY AS SPECIFIED
@router.post("/send")
async def perfect_chat_endpoint(request: ChatRequest):
    """
    🧱 PERFECT CHAT PIPELINE IMPLEMENTATION
    ⚡ WITH INTENT-BASED SERVICE LOADING
    
    Follows exact specification:
    1. Backend receives message
    2. Identify userId 
    3. ⚡ DETECT INTENT - load ONLY required services
    4. Fetch from required services only (Redis → Neo4j → Pinecone cascade)
    5. Build combined context
    6. Send to AI model
    7. Save: Conversation in Mongo, Embedded memory in Pinecone, Relationship updates in Neo4j
    8. Return reply to frontend
    
    🟢 Complete user separation guaranteed
    🟢 No duplicates allowed
    🟢 Multi-database coordination
    ⚡ OPTIMIZED: Only loads services based on intent
    """
    try:
        # Step 1: Backend receives message & identify user
        session_id = request.session_id or str(uuid.uuid4())
        
        # Find user by email (primary unique identifier)
        user = await users_collection.find_one({"email": request.user_email})
        if not user:
            raise HTTPException(status_code=404, detail=f"User not found: {request.user_email}")
        
        user_id = str(user["_id"])
        
        print(f"🚀 Processing chat for user: {request.user_email} (ID: {user_id})")
        
        # ⚡ STEP 2: DETECT INTENT - Load only required services
        from app.services.intent_detector import load_services_for_message, get_cached_or_query
        services = await load_services_for_message(request.message)
        intent = services["intent"]
        
        print(f"🎯 Intent: {intent.value}, Loading: {list(services.keys())}")
        
        # ⚡ STEP 3: CASCADE QUERY - Check cache first, stop if found
        memory_context = ""
        user_memory = None
        
        # Try Redis cache first (fastest)
        cache_key = f"chat_context:{user_id}"
        cached_context = await get_cached_or_query(
            user_id=user_id,
            query_type="personal",
            redis_key=cache_key
        )
        
        if cached_context:
            # ✅ Found in cache - STOP, don't query other services
            print("✅ Using cached context (no Neo4j/Pinecone query)")
            user_memory = cached_context
            memory_context = memory_manager.build_context_for_model(cached_context)
        elif "neo4j" in services:
            # Only load Neo4j if intent requires it
            print("🔵 Loading from Neo4j (intent requires personal memory)")
            user_memory = await memory_manager.load_user_memory(user_id)
            memory_context = memory_manager.build_context_for_model(user_memory)
        
        # Enhanced prompt with memory
        enhanced_prompt = f"""
=== USER MEMORY CONTEXT ===
{memory_context}

=== CURRENT MESSAGE ===
User: {request.message}

Provide a helpful, personalized response based on the user's memory and context.
"""
        
        # Get AI response
        ai_response = await get_llm_response(enhanced_prompt)
        
        # 🚀 PARALLEL PROCESSING: Run these in background (non-blocking)
        # 1. Save conversation (fast, can run in parallel)
        # 2. Extract and save user details (runs in background, doesn't block)
        import asyncio
        
        # Create background tasks
        background_tasks = []
        
        # Task 1: Save conversation
        background_tasks.append(
            memory_manager.save_conversation(user_id, request.message, ai_response)
        )
        
        # Task 2: Extract and save user details (runs in parallel, non-blocking)
        from app.services.user_detail_extractor import extract_and_save_user_details_async
        background_tasks.append(
            extract_and_save_user_details_async(user_id, request.message, ai_response)
        )
        
        # Execute all background tasks in parallel (fire and forget)
        # Don't await - let them run in background
        asyncio.create_task(asyncio.gather(*background_tasks, return_exceptions=True))
        print(f"🚀 Background tasks started: conversation save + user detail extraction")
        
        # Format response for frontend (immediate return, doesn't wait for background tasks)
        response = ChatResponse(
            reply=ai_response,
            intent="memory_enhanced",
            success=True,
            session_id=session_id,
            message_id=None,
            debug_info={
                "memory_context_loaded": len(memory_context) > 0,
                "user_memory_available": bool(user_memory),
                "processing_success": True,
                "background_tasks": "extraction_and_memory_update_started"
            }
        )
        
        print(f"✅ Chat processed successfully for {request.user_email}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

# 🎯 NEW PERFECT ENDPOINTS FOR COMPLETE USER MANAGEMENT

@router.post("/send-message")
async def send_message_perfect(request: SendMessageRequest):
    """
    🧠 MEMORY-ENHANCED MESSAGE PROCESSING
    
    This endpoint now:
    1. Loads ALL user memory (MongoDB + Redis + Pinecone + Neo4j)
    2. Injects memory context into AI model
    3. Processes memory update instructions from AI
    4. Updates all databases safely
    """
    try:
        user_id = request.userId
        session_id = request.sessionId
        user_message = request.message
        
        # 🟩 Step 1: Load ALL user memory for context injection
        print(f"🧠 Loading complete memory for user: {user_id}")
        user_memory = await memory_manager.load_user_memory(user_id)
        
        # 🟩 Step 2: Build comprehensive context for AI model
        memory_context = memory_manager.build_context_for_model(user_memory)
        
        # 🟩 Step 3: Create enhanced prompt with memory context
        enhanced_prompt = f"""
You are a helpful AI assistant with access to the user's complete memory and profile.

=== USER MEMORY CONTEXT ===
{memory_context}

=== CURRENT MESSAGE ===
User: {user_message}

=== INSTRUCTIONS ===
- Use the memory context to provide personalized responses
- If user asks "what do you know about me", use the memory context
- If you learn something important, generate memory update instructions
- Be natural and conversational, don't mention technical memory details

=== MEMORY UPDATE FORMAT ===
If you need to update memories, end your response with:
[MEMORY_UPDATE]
{{
  "updateMongo": {{"key": "value"}},
  "addStructuredMemory": {{"type": "preference", "value": "something"}},
  "addVectorMemory": "Important fact about user",
  "addGraphMemory": ["RELATIONSHIP_TYPE", "target_value"],
  "addTempMemory": {{"session_note": "temporary_value"}}
}}
[/MEMORY_UPDATE]

Respond naturally:
"""
        
        # 🟩 Step 4: Get AI response with memory context
        ai_response = await get_llm_response(enhanced_prompt)
        
        # 🟩 Step 5: Extract memory update instructions if present
        memory_updates = {}
        if "[MEMORY_UPDATE]" in ai_response:
            try:
                parts = ai_response.split("[MEMORY_UPDATE]")
                clean_response = parts[0].strip()
                memory_instruction_text = parts[1].split("[/MEMORY_UPDATE]")[0].strip()
                memory_updates = json.loads(memory_instruction_text)
                ai_response = clean_response
            except Exception as e:
                print(f"⚠️ Error parsing memory updates: {e}")
        
        # 🟩 Step 6: Process memory updates safely
        if memory_updates:
            print(f"📝 Processing memory updates for user: {user_id}")
            update_results = await memory_manager.process_memory_update_instructions(user_id, memory_updates)
            print(f"✅ Memory update results: {update_results}")
        
        # 🟩 Step 7: Save conversation to MongoDB (parallel with extraction)
        # 🚀 PARALLEL PROCESSING: Run memory save and user extraction in background
        import asyncio
        
        # Create background tasks for parallel execution
        background_tasks = []
        
        # Task 1: Save conversation
        background_tasks.append(
            memory_manager.save_conversation(user_id, user_message, ai_response, memory_updates)
        )
        
        # Task 2: Extract and save user details (runs in parallel, non-blocking)
        from app.services.user_detail_extractor import extract_and_save_user_details_async
        background_tasks.append(
            extract_and_save_user_details_async(user_id, user_message, ai_response)
        )
        
        # Task 3: Process memory updates in background if present
        if memory_updates:
            background_tasks.append(
                memory_manager.process_memory_update_instructions(user_id, memory_updates)
            )
        
        # Execute all background tasks in parallel (fire and forget - don't block response)
        asyncio.create_task(asyncio.gather(*background_tasks, return_exceptions=True))
        print(f"🚀 Background tasks started: conversation save + user detail extraction + memory updates")
        
        return {
            "success": True,
            "response": ai_response,
            "sessionId": session_id,
            "debug": {
                "user_memory_loaded": bool(user_memory),
                "memory_update_instructions": memory_updates,
                "context_length": len(memory_context),
                "background_tasks": "extraction_and_memory_update_started"
            }
        }
        
    except Exception as e:
        print(f"❌ Memory-enhanced chat error: {e}")
        return {"error": f"Memory processing failed: {str(e)}", "success": False}


@router.get("/memory-test/{user_id}")
async def test_user_memory(user_id: str):
    """
    🧪 TEST ENDPOINT: Check what memories are available for a user
    
    Use this to debug memory loading and see what context the AI has access to.
    """
    try:
        # Load user memory
        user_memory = await memory_manager.load_user_memory(user_id)
        
        # Build context
        memory_context = memory_manager.build_context_for_model(user_memory)
        
        return {
            "success": True,
            "user_id": user_id,
            "raw_memory": user_memory,
            "formatted_context": memory_context,
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
            }
        }
        
    except Exception as e:
        return {"error": f"Memory test failed: {str(e)}", "success": False}


@router.post("/memory-update/{user_id}")
async def manual_memory_update(user_id: str, updates: Dict[str, Any] = Body(...)):
    """
    🛠️ MANUAL MEMORY UPDATE ENDPOINT
    
    Allows manual testing of memory update functionality.
    
    Example request body:
    {
        "updateMongo": {"location": "Bangalore"},
        "addStructuredMemory": {"type": "preference", "value": "likes coffee"},
        "addVectorMemory": "User loves programming in Python",
        "addGraphMemory": ["INTERESTED_IN", "Machine Learning"]
    }
    """
    try:
        results = await memory_manager.process_memory_update_instructions(user_id, updates)
        
        return {
            "success": True,
            "user_id": user_id,
            "update_results": results,
            "instructions_processed": list(updates.keys())
        }
        
    except Exception as e:
        return {"error": f"Manual memory update failed: {str(e)}", "success": False}


@router.get("/memory-test/{user_id}")
async def test_user_memory(user_id: str):
    """
    🧪 TEST ENDPOINT: Check what memories are available for a user
    
    Use this to debug memory loading and see what context the AI has access to.
    """
    try:
        # Load user memory
        user_memory = await memory_manager.load_user_memory(user_id)
        
        # Build context
        memory_context = memory_manager.build_context_for_model(user_memory)
        
        return {
            "success": True,
            "user_id": user_id,
            "raw_memory": user_memory,
            "formatted_context": memory_context,
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
            }
        }
        
    except Exception as e:
        return {"error": f"Memory test failed: {str(e)}", "success": False}


@router.post("/memory-update/{user_id}")
async def manual_memory_update(user_id: str, updates: Dict[str, Any] = Body(...)):
    """
    🛠️ MANUAL MEMORY UPDATE ENDPOINT
    
    Allows manual testing of memory update functionality.
    
    Example request body:
    {
        "updateMongo": {"location": "Bangalore"},
        "addStructuredMemory": {"type": "preference", "value": "likes coffee"},
        "addVectorMemory": "User loves programming in Python",
        "addGraphMemory": ["INTERESTED_IN", "Machine Learning"]
    }
    """
    try:
        results = await memory_manager.process_memory_update_instructions(user_id, updates)
        
        return {
            "success": True,
            "user_id": user_id,
            "update_results": results,
            "instructions_processed": list(updates.keys())
        }
        
    except Exception as e:
        return {"error": f"Manual memory update failed: {str(e)}", "success": False}

@router.get("/user-summary/{user_id}")
async def get_user_complete_summary(user_id: str):
    """
    🎯 Get complete user summary from all databases.
    Perfect for user profile display.
    """
    try:
        # TODO: Implement get_user_summary from memory pipeline
        # For now, return basic user info
        return {
            "success": True,
            "data": {
                "userId": user_id,
                "message": "User summary endpoint - memory pipeline integration pending"
            }
        }
    except Exception as e:
        return {"error": str(e), "success": False}

@router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str, limit: int = 20):
    """
    Get all chat sessions for a user.
    🟢 Rule: Only return sessions for the specified userId
    ✨ OPTIMIZED: Uses projections for smaller payloads (Part 9)
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        # 🚀 Part 9: Projection - fetch only needed fields
        projection = {
            "sessionId": 1,
            "updatedAt": 1,
            "createdAt": 1,
            "messages": {"$slice": -5},  # Only last 5 messages for preview
            # Exclude heavy fields
            "_id": 0,
            "userId": 0
        }
        
        sessions = await sessions_collection.find(
            {"userId": ObjectId(user_id)},
            projection
        ).sort("updatedAt", -1).limit(limit).to_list(length=limit)
        
        # Format sessions for frontend
        formatted_sessions = []
        for session in sessions:
            formatted_session = {
                "sessionId": session["sessionId"],
                "messageCount": len(session.get("messages", [])),
                "lastMessage": "",
                "updatedAt": session["updatedAt"],
                "createdAt": session["createdAt"]
            }
            
            # Get last message preview
            messages = session.get("messages", [])
            if messages:
                last_msg = messages[-1]
                formatted_session["lastMessage"] = last_msg.get("text", "")[:100]
            
            formatted_sessions.append(formatted_session)
        
        return {
            "success": True,
            "sessions": formatted_sessions,
            "total": len(formatted_sessions)
        }
        
    except Exception as e:
        return {"error": str(e), "success": False}

@router.get("/session/{session_id}/messages")
async def get_session_messages(session_id: str, user_id: str):
    """
    Get all messages in a session.
    🟢 Rule: Verify session belongs to user (prevent data mixing)
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        session = await sessions_collection.find_one({
            "sessionId": session_id,
            "userId": ObjectId(user_id)  # CRITICAL: Verify ownership
        })
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or access denied")
        
        messages = session.get("messages", [])
        
        return {
            "success": True,
            "sessionId": session_id,
            "messages": messages,
            "messageCount": len(messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e), "success": False}

@router.delete("/session/{session_id}")
async def delete_session(session_id: str, user_id: str):
    """
    Delete a chat session.
    🟢 Rule: Only delete if session belongs to user
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        
        result = await sessions_collection.delete_one({
            "sessionId": session_id,
            "userId": ObjectId(user_id)  # CRITICAL: Verify ownership
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Session not found or access denied")
        
        return {
            "success": True,
            "message": "Session deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e), "success": False}
        
        # Add memory context to request
        request.user_context = {
            "profile": {
                "username": user.get("username", ""),
                "hobby": user.get("hobby", []),
                "role": user.get("role", ""),
                "interests": user.get("interests", []),
                "responseStyle": user.get("responseStyle", "")
            },
            "memory": [item["content"] for item in memory_items],
            "conversation_history": conversation_history
        }
        
        # Save user message to session
        user_message = {
            "messageId": str(uuid.uuid4()),
            "role": "user",
            "content": request.message,
            "timestamp": datetime.utcnow(),
            "metadata": {}
        }
        
        # Process chat with enhanced context
        response_data = await process_chat(request)
        
        # Save assistant response to session
        assistant_message = {
            "messageId": str(uuid.uuid4()),
            "role": "assistant",
            "content": response_data["reply"],
            "timestamp": datetime.utcnow(),
            "metadata": {
                "intent": response_data["intent"],
                "debug_info": response_data.get("debug_info", {})
            }
        }
        
        # Update session with new messages
        await sessions_collection.update_one(
            {"sessionId": session_id, "user_id": user_id},
            {
                "$push": {
                    "messages": {"$each": [user_message, assistant_message]}
                },
                "$set": {
                    "updatedAt": datetime.utcnow()
                }
            }
        )
        
        # Check if we should add anything to user memory
        await update_user_memory_from_chat(user_id, request.message, response_data["reply"])
        
        # Return enhanced response
        return ChatResponse(
            reply=response_data["reply"],
            intent=response_data["intent"],
            success=True,
            session_id=session_id,
            message_id=assistant_message["messageId"],
            debug_info=response_data.get("debug_info", {})
        )
        
    except Exception as e:
        return ChatResponse(
            reply="I'm having trouble right now. Please try again shortly.",
            intent="error",
            success=False,
            debug_info={"error": str(e)}
        )

# 💾 SESSION MANAGEMENT ENDPOINTS
@router.get("/sessions")
async def get_user_sessions(user_id: str, limit: int = 20):
    """Get user's chat sessions"""
    sessions = await sessions_collection.find(
        {"user_id": user_id, "isActive": True}
    ).sort("updatedAt", -1).limit(limit).to_list(limit)
    
    # Convert ObjectId to string and get message count
    for session in sessions:
        session["_id"] = str(session["_id"])
        session["messageCount"] = len(session.get("messages", []))
        # Remove messages from list view for performance
        session.pop("messages", None)
    
    return {"sessions": sessions}

@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str, user_id: str, limit: int = 50):
    """
    Get detailed session with messages, highlights, and mini agents in ONE request.
    ✨ OPTIMIZED: Batch loading with caching for maximum performance.
    """
    session = await sessions_collection.find_one({
        "sessionId": session_id,
        "user_id": user_id
    })
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session["_id"] = str(session["_id"])
    
    # Limit messages for performance (get latest messages)
    messages = session.get("messages", [])
    if limit and len(messages) > limit:
        messages = messages[-limit:]
    
    session["messages"] = messages
    
    # 🚀 OPTIMIZED: Try to get highlights from cache first
    # ⏱️ FAIL FAST: 100ms timeout for Redis cache check
    highlights = await tracked_timeout(
        cache_service.get_highlights(session_id),
        timeout_ms=TimeoutConfig.REDIS_GET,
        service_name="Redis GET (highlights)",
        fallback=None
    )
    if highlights is None:
        # Cache miss - fetch from database
        # ⏱️ FAIL FAST: 300ms timeout for MongoDB query
        print(f"💾 Fetching highlights from database")
        highlights = await tracked_timeout(
            highlights_collection.find(
                {"sessionId": session_id}
            ).to_list(length=None),
            timeout_ms=TimeoutConfig.MONGODB_FIND,
            service_name="MongoDB FIND (highlights)",
            fallback=[]
        )
        
        for highlight in highlights:
            highlight["_id"] = str(highlight["_id"])
        
        # Cache for future requests
        # ⏱️ FAIL FAST: 100ms timeout for Redis cache set
        await tracked_timeout(
            cache_service.set_highlights(session_id, highlights),
            timeout_ms=TimeoutConfig.REDIS_SET,
            service_name="Redis SET (highlights)",
            fallback=False
        )
    
    session["highlights"] = highlights
    
    # 🚀 OPTIMIZED: Try to get mini agents from cache first
    # ⏱️ FAIL FAST: 100ms timeout for Redis cache check
    mini_agents = await tracked_timeout(
        cache_service.get_mini_agents(session_id),
        timeout_ms=TimeoutConfig.REDIS_GET,
        service_name="Redis GET (mini agents)",
        fallback=None
    )
    if mini_agents is None:
        # Cache miss - fetch from database
        # ⏱️ FAIL FAST: 300ms timeout for MongoDB query
        print(f"💾 Fetching mini agents from database")
        agents = await tracked_timeout(
            mini_agents_collection.find(
                {"sessionId": session_id}
            ).to_list(length=None),
            timeout_ms=TimeoutConfig.MONGODB_FIND,
            service_name="MongoDB FIND (mini agents)",
            fallback=[]
        )
        
        # Serialize mini agents
        mini_agents = []
        for agent in agents:
            serialized_messages = []
            for msg in agent.get("messages", []):
                serialized_msg = {
                    "id": msg.get("id"),
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp").isoformat() if isinstance(msg.get("timestamp"), datetime) else msg.get("timestamp")
                }
                serialized_messages.append(serialized_msg)
            
            mini_agents.append({
                "agentId": agent["agentId"],
                "messageId": agent["messageId"],
                "selectedText": agent["selectedText"],
                "messages": serialized_messages,
                "hasConversation": agent.get("hasConversation", len(agent.get("messages", [])) > 0),
                "createdAt": agent["createdAt"].isoformat() if isinstance(agent["createdAt"], datetime) else agent["createdAt"],
                "updatedAt": agent["updatedAt"].isoformat() if isinstance(agent["updatedAt"], datetime) else agent["updatedAt"],
            })
        
        # Cache for future requests
        await cache_service.set_mini_agents(session_id, mini_agents)
    
    session["miniAgents"] = mini_agents
    
    print(f"✅ Session loaded with {len(highlights)} highlights and {len(mini_agents)} mini agents")
    
    return session

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user_id: str):
    """Delete a session (soft delete)"""
    result = await sessions_collection.update_one(
        {"sessionId": session_id, "user_id": user_id},
        {"$set": {"isActive": False, "deletedAt": datetime.utcnow()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "deleted"}

# 🎨 HIGHLIGHT MANAGEMENT ENDPOINTS
@router.post("/highlights", status_code=201)
async def create_highlight(
    request: HighlightRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Create a new highlight with exact character positions.
    Stores startIndex and endIndex for accurate persistence.
    ✨ OPTIMIZED: Invalidates cache after creation for data consistency.
    """
    try:
        user_id = ObjectId(current_user.user_id)
        
        # Create unique key to prevent duplicates
        unique_key = f"{request.sessionId}_{request.messageId}_{request.startIndex}_{request.endIndex}"
        
        # Check if highlight already exists
        existing = await highlights_collection.find_one({"uniqueKey": unique_key})
        if existing:
            return {
                "status": "exists",
                "highlightId": existing["highlightId"],
                "highlight": {
                    "highlightId": existing["highlightId"],
                    "messageId": existing["messageId"],
                    "text": existing["text"],
                    "color": existing["color"],
                    "startIndex": existing["startIndex"],
                    "endIndex": existing["endIndex"],
                }
            }
        
        highlight = {
            "highlightId": str(uuid.uuid4()),
            "uniqueKey": unique_key,
            "sessionId": request.sessionId,
            "messageId": request.messageId,
            "userId": user_id,
            "user_id": user_id,  # Compatibility
            "text": request.text,
            "color": request.color,
            "startIndex": request.startIndex,
            "endIndex": request.endIndex,
            "createdAt": datetime.utcnow()
        }
        
        await highlights_collection.insert_one(highlight)
        
        # 🗑️ Invalidate cache after creating highlight
        await cache_service.invalidate_highlights(request.sessionId)
        print(f"🔄 Cache invalidated for session: {request.sessionId}")
        
        return {
            "status": "created",
            "highlightId": highlight["highlightId"],
            "highlight": {
                "highlightId": highlight["highlightId"],
                "messageId": highlight["messageId"],
                "text": highlight["text"],
                "color": highlight["color"],
                "startIndex": highlight["startIndex"],
                "endIndex": highlight["endIndex"],
            }
        }
    except Exception as e:
        print(f"❌ Error creating highlight: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create highlight: {str(e)}")

@router.get("/highlights/{session_id}")
async def get_session_highlights(
    session_id: str,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Get all highlights for a session.
    Returns highlights with exact startIndex and endIndex for rendering.
    ✨ OPTIMIZED: Uses Redis caching + compound indexes for lightning-fast retrieval.
    """
    try:
        user_id = ObjectId(current_user.user_id)
        
        # 🚀 STEP 1: Check cache first
        cached_highlights = await cache_service.get_highlights(session_id)
        if cached_highlights is not None:
            print(f"⚡ Cache HIT - returning {len(cached_highlights)} highlights")
            return {"highlights": cached_highlights}
        
        # 🔍 STEP 2: Cache miss - fetch from database
        print(f"💾 Cache MISS - fetching from database")
        
        # Use projection to fetch only needed fields (reduces data transfer)
        # Use compound index: sessionId + user_id for optimal performance
        highlights = await highlights_collection.find(
            {
                "sessionId": session_id,
                "$or": [{"userId": user_id}, {"user_id": user_id}]
            },
            {
                "_id": 0,  # Exclude MongoDB _id
                "highlightId": 1,
                "messageId": 1,
                "text": 1,
                "color": 1,
                "startIndex": 1,
                "endIndex": 1,
                "note": 1,
                "createdAt": 1
            }
        ).to_list(length=None)
        
        # 📦 STEP 3: Cache the results for future requests
        await cache_service.set_highlights(session_id, highlights)
        
        print(f"✅ Fetched and cached {len(highlights)} highlights")
        return {"highlights": highlights}
    except Exception as e:
        print(f"❌ Error fetching highlights: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch highlights: {str(e)}")

@router.delete("/highlights/{highlight_id}")
async def delete_highlight(
    highlight_id: str,
    current_user: User = Depends(get_current_user_from_session)
):
    """Delete a highlight by ID and invalidate cache"""
    try:
        user_id = ObjectId(current_user.user_id)
        
        # Fetch highlight first to get session_id for cache invalidation
        highlight = await highlights_collection.find_one({
            "highlightId": highlight_id,
            "$or": [{"userId": user_id}, {"user_id": user_id}]
        })
        
        if not highlight:
            raise HTTPException(status_code=404, detail="Highlight not found")
        
        session_id = highlight.get("sessionId")
        
        result = await highlights_collection.delete_one({
            "highlightId": highlight_id,
            "$or": [{"userId": user_id}, {"user_id": user_id}]
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Highlight not found")
        
        # 🗑️ Invalidate cache after deletion
        if session_id:
            await cache_service.invalidate_highlights(session_id)
            print(f"🔄 Cache invalidated for session: {session_id}")
        
        return {"status": "deleted", "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting highlight: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete highlight: {str(e)}")

@router.patch("/highlights/{highlight_id}/note")
async def update_highlight_note(
    highlight_id: str,
    request: dict,
    current_user: User = Depends(get_current_user_from_session)
):
    """Update or delete a note for a highlight"""
    try:
        user_id = ObjectId(current_user.user_id)
        note = request.get("note", "")
        
        # Update the highlight note
        result = await highlights_collection.update_one(
            {
                "highlightId": highlight_id,
                "$or": [{"userId": user_id}, {"user_id": user_id}]
            },
            {"$set": {"note": note if note else None}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Highlight not found")
        
        return {"status": "updated", "highlightId": highlight_id, "note": note}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating highlight note: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update note: {str(e)}")

# 🤖 MINI-AGENT ENDPOINTS - MongoDB Storage with Real AI Responses
# Import Mini Agent service for isolated conversation handling
from app.services.mini_agent_service import mini_agent_service

class CreateMiniAgentRequest(BaseModel):
    messageId: str  # The Main Agent message this Mini Agent is tied to
    sessionId: str  # Chat session ID where the message belongs
    selectedText: str  # The text snippet user selected
    userPrompt: str = ""  # Optional initial question

class MiniAgentMessageRequest(BaseModel):
    content: str  # User's query to Mini Agent

@router.post("/mini-agent/create", status_code=201)
async def create_mini_agent(
    request: CreateMiniAgentRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Create a new Mini Agent conversation thread.
    
    🎯 ARCHITECTURE:
    - Each Mini Agent is permanently tied to ONE message_id
    - Uses same AI pipeline as Main Agent but maintains isolated context
    - Never mixes with Main Agent conversation
    - Stores in MongoDB - single source of truth
    - Persists across refresh
    
    🔒 ISOLATION GUARANTEE:
    - Mini Agent has its own conversation history
    - Main Agent never receives Mini Agent messages
    - No cross-contamination of contexts
    """
    try:
        user_id = ObjectId(current_user.user_id)
        session_id = request.sessionId
        message_id = request.messageId
        
        print(f"🤖 Create/Get Mini Agent for message: {message_id}")
        
        # 🔒 STRICT RULE: One Mini Agent per Message ID
        # Check if Mini Agent already exists for this message
        existing_agent = await mini_agents_collection.find_one({
            "messageId": message_id,
            "$or": [{"userId": user_id}, {"user_id": user_id}]
        })
        
        if existing_agent:
            print(f"♻️ Mini Agent already exists for message {message_id}, returning existing agent")
            
            # Update snippet if new text provided (user selected different text)
            if request.selectedText != existing_agent.get("selectedText"):
                await mini_agents_collection.update_one(
                    {"agentId": existing_agent["agentId"]},
                    {
                        "$set": {
                            "selectedText": request.selectedText,
                            "updatedAt": datetime.utcnow()
                        }
                    }
                )
                print(f"📝 Updated snippet for existing Mini Agent")
            
            # Serialize messages properly
            serialized_messages = []
            for msg in existing_agent.get("messages", []):
                serialized_msg = {
                    "id": msg.get("id"),
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp").isoformat() if isinstance(msg.get("timestamp"), datetime) else msg.get("timestamp")
                }
                serialized_messages.append(serialized_msg)
            
            return {
                "agentId": existing_agent["agentId"],
                "messageId": existing_agent["messageId"],
                "selectedText": request.selectedText,  # Return updated snippet
                "messages": serialized_messages,
                "hasConversation": existing_agent.get("hasConversation", False),
                "createdAt": existing_agent["createdAt"].isoformat() if isinstance(existing_agent.get("createdAt"), datetime) else existing_agent.get("createdAt"),
                "isExisting": True  # Flag to indicate this is reused
            }
        
        # No existing agent, create new one
        agent_id = str(uuid.uuid4())  # Unique mini_agent_session_id
        print(f"✨ Creating NEW Mini Agent: {agent_id} for message: {message_id}")
        
        # Verify session belongs to user (security check)
        session = await sessions_collection.find_one({
            "$and": [
                {"$or": [{"chat_id": session_id}, {"sessionId": session_id}]},
                {"$or": [{"user_id": user_id}, {"userId": user_id}]}
            ]
        })
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
        # Verify message exists in the session (validation)
        message_exists = any(
            msg.get('id') == message_id or msg.get('messageId') == message_id
            for msg in session.get('messages', [])
        )
        
        if not message_exists:
            print(f"⚠️ Warning: Message {message_id} not found in session {session_id}")
        
        # Create Mini Agent with isolated conversation context
        # Start with empty messages - user will ask when ready
        mini_agent = {
            "agentId": agent_id,  # Unique mini_agent_session_id per spec
            "messageId": message_id,  # Tied to this Main Agent message
            "sessionId": session_id,  # Parent chat session
            "userId": user_id,
            "user_id": user_id,  # Compatibility field
            "selectedText": request.selectedText,  # The snippet (editable/removable)
            "messages": [],  # Isolated conversation history
            "hasConversation": False,  # Track if any messages exchanged
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }
        
        # Store in MongoDB (single source of truth)
        result = await mini_agents_collection.insert_one(mini_agent)
        
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create mini-agent in database")
        
        # 🗑️ Invalidate cache after creating mini agent
        await cache_service.invalidate_mini_agents(session_id)
        print(f"🔄 Cache invalidated for session: {session_id}")
        
        print(f"✅ Mini Agent {agent_id} created and stored in MongoDB")
        
        return {
            "agentId": agent_id,
            "messageId": message_id,
            "selectedText": request.selectedText,
            "messages": [],
            "hasConversation": False,
            "createdAt": mini_agent["createdAt"].isoformat(),
            "isExisting": False  # Flag to indicate this is new
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating mini-agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create mini-agent: {str(e)}")

@router.get("/mini-agent/{agent_id}")
async def get_mini_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Get Mini Agent conversation thread.
    
    🟢 Fetches from MongoDB - single source of truth
    🔒 Returns isolated conversation history (never Main Agent messages)
    """
    try:
        user_id = ObjectId(current_user.user_id)
        
        agent = await mini_agents_collection.find_one({
            "agentId": agent_id,
            "$or": [{"userId": user_id}, {"user_id": user_id}]
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="Mini-agent not found")
        
        # Serialize messages properly (convert datetime to ISO format)
        serialized_messages = []
        for msg in agent.get("messages", []):
            serialized_msg = {
                "id": msg.get("id"),
                "role": msg.get("role"),
                "content": msg.get("content"),
                "timestamp": msg.get("timestamp").isoformat() if isinstance(msg.get("timestamp"), datetime) else msg.get("timestamp")
            }
            serialized_messages.append(serialized_msg)
        
        return {
            "agentId": agent["agentId"],
            "messageId": agent["messageId"],
            "sessionId": agent.get("sessionId"),
            "selectedText": agent["selectedText"],
            "messages": serialized_messages,
            "hasConversation": agent.get("hasConversation", len(agent.get("messages", [])) > 0),
            "createdAt": agent["createdAt"].isoformat() if isinstance(agent["createdAt"], datetime) else agent["createdAt"],
            "updatedAt": agent["updatedAt"].isoformat() if isinstance(agent["updatedAt"], datetime) else agent["updatedAt"],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching mini-agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch mini-agent: {str(e)}")

@router.post("/mini-agent/{agent_id}/message")
async def send_mini_agent_message(
    agent_id: str,
    request: MiniAgentMessageRequest,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Send a message to Mini Agent and get AI response.
    
    🎯 ISOLATION GUARANTEE:
    - Uses Mini Agent Service with isolated conversation context
    - Never accesses Main Agent history
    - Uses same AI pipeline but completely separate context
    - Mini Agent only sees its own conversation history
    
    📨 BEHAVIOR PER SPEC:
    - If query is RELATED to selected text: Explains that text
    - If query is UNRELATED: Answers normally (Mini Agent is helpful, not restrictive)
    """
    try:
        user_id = ObjectId(current_user.user_id)
        
        # Fetch Mini Agent from MongoDB (single source of truth)
        agent = await mini_agents_collection.find_one({
            "agentId": agent_id,
            "$or": [{"userId": user_id}, {"user_id": user_id}]
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="Mini-agent not found")
        
        print(f"💬 Processing Mini Agent message for agent: {agent_id}")
        
        # Create user message with unique ID
        user_message = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": request.content,
            "timestamp": datetime.utcnow(),
        }
        
        # Get Mini Agent's isolated conversation history
        # CRITICAL: This is ONLY Mini Agent's own messages, never Main Agent's
        mini_agent_history = agent.get("messages", [])
        
        # Use Mini Agent Service to generate response
        # This ensures complete isolation from Main Agent
        ai_response_content = await mini_agent_service.generate_response(
            selected_text=agent['selectedText'],
            user_query=request.content,
            conversation_history=mini_agent_history,
            message_id=agent['messageId']
        )
        
        # Create AI message
        ai_message = {
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": ai_response_content,
            "timestamp": datetime.utcnow(),
        }
        
        # Update Mini Agent in MongoDB
        # Append both messages and mark conversation as started
        await mini_agents_collection.update_one(
            {"agentId": agent_id},
            {
                "$push": {"messages": {"$each": [user_message, ai_message]}},
                "$set": {
                    "updatedAt": datetime.utcnow(),
                    "hasConversation": True  # Track that conversation has started
                }
            }
        )
        
        # 🗑️ Invalidate both mini agents cache and single agent cache
        session_id = agent.get("sessionId")
        if session_id:
            await cache_service.invalidate_mini_agents(session_id)
        await cache_service.invalidate_single_mini_agent(agent_id)
        print(f"🔄 Cache invalidated for agent: {agent_id}")
        
        print(f"✅ Mini Agent response generated and stored")
        
        # Optional: Generate learning metadata for Main Agent (background)
        # This sends METADATA only, never messages
        try:
            updated_history = mini_agent_history + [user_message, ai_message]
            metadata = await mini_agent_service.generate_metadata_for_main_agent(
                mini_agent_history=updated_history,
                user_id=str(user_id)
            )
            
            if metadata:
                # Store metadata separately (not in Main Agent conversation)
                # This can be used by Main Agent for learning but won't contaminate messages
                # TODO: Implement metadata storage if needed
                print(f"📊 Generated learning metadata: {metadata}")
        except Exception as meta_error:
            # Don't fail the request if metadata generation fails
            print(f"⚠️ Metadata generation failed (non-critical): {meta_error}")
        
        return {
            "userMessage": {
                "id": user_message["id"],
                "role": user_message["role"],
                "content": user_message["content"],
                "timestamp": user_message["timestamp"].isoformat(),
            },
            "aiMessage": {
                "id": ai_message["id"],
                "role": ai_message["role"],
                "content": ai_message["content"],
                "timestamp": ai_message["timestamp"].isoformat(),
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error sending mini-agent message: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.delete("/mini-agent/{agent_id}", status_code=200)
async def delete_mini_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Delete Mini Agent conversation.
    
    🟢 Hard delete from MongoDB - removes entire thread
    🔄 Returns message_id so frontend can remove icon instantly
    """
    try:
        user_id = ObjectId(current_user.user_id)
        
        print(f"🗑️ Deleting Mini Agent: {agent_id}")
        
        # First, get the agent to return messageId
        agent = await mini_agents_collection.find_one({
            "agentId": agent_id,
            "$or": [{"userId": user_id}, {"user_id": user_id}]
        })
        
        if not agent:
            raise HTTPException(status_code=404, detail="Mini-agent not found")
        
        message_id = agent.get("messageId")
        session_id = agent.get("sessionId")
        
        # Delete from MongoDB
        result = await mini_agents_collection.delete_one({
            "agentId": agent_id,
            "$or": [{"userId": user_id}, {"user_id": user_id}]
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Failed to delete from database")
        
        # 🗑️ Invalidate caches after deletion
        if session_id:
            await cache_service.invalidate_mini_agents(session_id)
        await cache_service.invalidate_single_mini_agent(agent_id)
        print(f"🔄 Cache invalidated for agent: {agent_id}")
        
        print(f"✅ Mini Agent {agent_id} deleted from database")
        
        return {
            "success": True,
            "message": "Mini-agent deleted successfully",
            "deleted": True,
            "agentId": agent_id,
            "messageId": message_id  # Return messageId for instant icon removal
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting mini-agent: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete mini-agent: {str(e)}")

@router.patch("/mini-agent/{agent_id}/snippet", status_code=200)
async def update_mini_agent_snippet(
    agent_id: str,
    request: dict,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Update Mini Agent's selected text snippet.
    
    🎯 USE CASE:
    - User selects new text from the same message while Mini Agent is open
    - Updates snippet without creating duplicate agent
    """
    try:
        user_id = ObjectId(current_user.user_id)
        new_snippet = request.get("selectedText", "")
        
        print(f"📝 Updating snippet for Mini Agent: {agent_id}")
        
        # Update snippet in database
        result = await mini_agents_collection.update_one(
            {
                "agentId": agent_id,
                "$or": [{"userId": user_id}, {"user_id": user_id}]
            },
            {
                "$set": {
                    "selectedText": new_snippet,
                    "updatedAt": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Mini-agent not found")
        
        print(f"✅ Snippet updated for Mini Agent {agent_id}")
        
        return {
            "success": True,
            "message": "Snippet updated successfully",
            "agentId": agent_id,
            "selectedText": new_snippet
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating snippet: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update snippet: {str(e)}")

@router.get("/mini-agents/session/{session_id}")
async def get_session_mini_agents(
    session_id: str,
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Get all Mini Agents for a specific chat session.
    
    🟢 Returns all Mini Agent threads organized by message ID
    🔒 Each Mini Agent is isolated and tied to ONE message_id
    🔄 Enables multiple Mini Agents to coexist independently
    ✨ OPTIMIZED: Uses Redis caching for instant retrieval
    """
    try:
        user_id = ObjectId(current_user.user_id)
        
        # 🚀 STEP 1: Check cache first
        cached_agents = await cache_service.get_mini_agents(session_id)
        if cached_agents is not None:
            print(f"⚡ Cache HIT - returning {len(cached_agents)} mini agents")
            return {"miniAgents": cached_agents}
        
        # 🔍 STEP 2: Cache miss - fetch from database
        print(f"💾 Cache MISS - fetching mini agents from database for session: {session_id}")
        
        # Find all Mini Agents for this session using compound index
        agents = await mini_agents_collection.find({
            "sessionId": session_id,
            "$or": [{"userId": user_id}, {"user_id": user_id}]
        }).to_list(length=None)
        
        # Serialize Mini Agents properly
        mini_agents = []
        for agent in agents:
            # Serialize messages
            serialized_messages = []
            for msg in agent.get("messages", []):
                serialized_msg = {
                    "id": msg.get("id"),
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp").isoformat() if isinstance(msg.get("timestamp"), datetime) else msg.get("timestamp")
                }
                serialized_messages.append(serialized_msg)
            
            mini_agents.append({
                "agentId": agent["agentId"],
                "messageId": agent["messageId"],
                "selectedText": agent["selectedText"],
                "messages": serialized_messages,
                "hasConversation": agent.get("hasConversation", len(agent.get("messages", [])) > 0),
                "createdAt": agent["createdAt"].isoformat() if isinstance(agent["createdAt"], datetime) else agent["createdAt"],
                "updatedAt": agent["updatedAt"].isoformat() if isinstance(agent["updatedAt"], datetime) else agent["updatedAt"],
            })
        
        # 📦 STEP 3: Cache the results for future requests
        await cache_service.set_mini_agents(session_id, mini_agents)
        
        print(f"✅ Fetched and cached {len(mini_agents)} Mini Agents for session {session_id}")
        
        return {"miniAgents": mini_agents}
        
    except Exception as e:
        print(f"❌ Error fetching session mini-agents: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch mini-agents: {str(e)}")


# 🔗 SHARING ENDPOINTS
@router.post("/share")
async def create_share_link(request: ShareRequest, user_id: str):
    """Create a shareable link for a conversation"""
    # Get session
    session = await sessions_collection.find_one({
        "sessionId": request.sessionId,
        "user_id": user_id
    })
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    share_data = {
        "sessionId": request.sessionId,
        "title": session.get("title", "Shared Conversation"),
        "messages": session.get("messages", []),
        "createdAt": session.get("createdAt"),
        "includeHighlights": request.includeHighlights
    }
    
    # Include highlights if requested
    if request.includeHighlights:
        highlights = await highlights_collection.find(
            {"sessionId": request.sessionId}
        ).to_list(length=None)
        
        for highlight in highlights:
            highlight["_id"] = str(highlight["_id"])
        
        share_data["highlights"] = highlights
    
    # Create share document
    share_id = str(uuid.uuid4())
    share_doc = {
        "shareId": share_id,
        "user_id": user_id,
        "data": share_data,
        "createdAt": datetime.utcnow(),
        "accessCount": 0
    }
    
    # Store in shares collection
    shares_collection = db.shared_conversations
    await shares_collection.insert_one(share_doc)
    
    share_url = f"https://yourapp.com/share/{share_id}"
    
    return {"status": "created", "shareUrl": share_url, "shareId": share_id}

@router.get("/share/{share_id}")
async def get_shared_conversation(share_id: str):
    """Get shared conversation (public endpoint)"""
    shares_collection = db.shared_conversations
    share_doc = await shares_collection.find_one({"shareId": share_id})
    
    if not share_doc:
        raise HTTPException(status_code=404, detail="Shared conversation not found")
    
    # Increment access count
    await shares_collection.update_one(
        {"shareId": share_id},
        {"$inc": {"accessCount": 1}}
    )
    
    return share_doc["data"]

# 🧠 HELPER FUNCTIONS
async def update_user_memory_from_chat(user_id: str, user_message: str, ai_response: str):
    """Analyze chat and update user memory if needed"""
    # Simple pattern matching for memory updates
    # In production, you'd use NLP to extract meaningful information
    
    memory_updates = []
    
    # Check for preferences or facts user mentions
    lower_message = user_message.lower()
    
    # Hobby/interest patterns
    hobby_patterns = ["i love", "i enjoy", "i like", "i'm into", "i play", "i watch"]
    for pattern in hobby_patterns:
        if pattern in lower_message:
            content = user_message[lower_message.find(pattern):].split('.')[0]
            memory_updates.append({
                "id": f"interest_{user_id}_{datetime.utcnow().timestamp()}",
                "user_id": user_id,
                "type": "preference",
                "content": content,
                "timestamp": datetime.utcnow(),
                "importance": 2
            })
            break
    
    # Location patterns
    location_patterns = ["i live in", "i'm from", "i'm in"]
    for pattern in location_patterns:
        if pattern in lower_message:
            content = user_message[lower_message.find(pattern):].split('.')[0]
            memory_updates.append({
                "id": f"location_{user_id}_{datetime.utcnow().timestamp()}",
                "user_id": user_id,
                "type": "fact",
                "content": content,
                "timestamp": datetime.utcnow(),
                "importance": 3
            })
            break
    
    # Save memory updates (deduplicated via upsert)
    if memory_updates:
        from app.routers.user import _upsert_memory_item
        for m in memory_updates:
            await _upsert_memory_item(user_id, m["content"], m["type"], m.get("importance", 1))