from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from app.models.highlight_models import (
    HighlightData, 
    CreateHighlightRequest, 
    MiniAgentThreadData, 
    MiniAgentMessageData,
    CreateMiniAgentThreadRequest,
    AddMiniAgentMessageRequest,
    ShareConversationRequest,
    HighlightResponse,
    MiniAgentResponse
)
from app.db.mongo_client import get_database
from app.utils.llm_client import get_llm_client

router = APIRouter(prefix="/api", tags=["highlights"])

def generate_highlight_id(session_id: str, message_id: str, start_index: int, end_index: int) -> str:
    """Generate unique highlight ID as specified"""
    return f"{session_id}_{message_id}_{start_index}_{end_index}"

def generate_mini_agent_title(selected_text: str) -> str:
    """Generate title from selected text"""
    words = selected_text.strip().split()[:4]
    if len(words) < 4:
        return " ".join(words)
    return " ".join(words) + "..."

@router.post("/highlights", response_model=dict)
async def create_highlight(request: CreateHighlightRequest):
    """Create a new highlight"""
    try:
        db = get_database()
        highlights_collection = db.highlights
        
        # Generate unique highlight ID
        highlight_id = generate_highlight_id(
            request.sessionId, request.messageId, request.startIndex, request.endIndex
        )
        
        # Check if highlight already exists (prevent duplicates)
        existing = highlights_collection.find_one({"highlightId": highlight_id})
        if existing:
            return {"success": False, "error": "Highlight already exists"}
        
        highlight_data = {
            "highlightId": highlight_id,
            "userId": request.userId,
            "sessionId": request.sessionId,
            "messageId": request.messageId,
            "startIndex": request.startIndex,
            "endIndex": request.endIndex,
            "color": request.color,
            "text": request.text,
            "note": request.note if request.note else None,
            "createdAt": datetime.utcnow()
        }
        
        result = highlights_collection.insert_one(highlight_data)
        
        if result.inserted_id:
            return {
                "success": True,
                "highlight": {
                    **highlight_data,
                    "createdAt": highlight_data["createdAt"].isoformat()
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create highlight")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating highlight: {str(e)}")

@router.get("/highlights/{session_id}", response_model=HighlightResponse)
async def get_highlights(session_id: str):
    """Get all highlights for a session"""
    try:
        db = get_database()
        highlights_collection = db.highlights
        
        highlights = list(highlights_collection.find(
            {"sessionId": session_id},
            {"_id": 0}  # Exclude MongoDB _id field
        ))
        
        # Convert datetime to ISO string
        for highlight in highlights:
            if "createdAt" in highlight:
                highlight["createdAt"] = highlight["createdAt"].isoformat()
        
        return HighlightResponse(highlights=highlights)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching highlights: {str(e)}")

@router.delete("/highlights/{highlight_id}")
async def delete_highlight(highlight_id: str):
    """Delete a highlight"""
    try:
        db = get_database()
        highlights_collection = db.highlights
        
        result = highlights_collection.delete_one({"highlightId": highlight_id})
        
        if result.deleted_count > 0:
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Highlight not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting highlight: {str(e)}")

@router.post("/mini-agents", response_model=dict)
async def create_mini_agent_thread(request: CreateMiniAgentThreadRequest):
    """Create a new mini-agent thread"""
    try:
        # Generate thread ID and title
        thread_id = f"thread_{request.sessionId}_{request.messageId}_{datetime.utcnow().timestamp()}"
        title = request.title or generate_mini_agent_title(request.selectedText)
        
        thread_data = {
            "id": thread_id,
            "sessionId": request.sessionId,
            "messageId": request.messageId,
            "title": title,
            "selectedText": request.selectedText,
            "messages": [],
            "createdAt": datetime.utcnow().isoformat()
        }
        
        # For now, just return the thread data without database storage
        # This allows testing of the API endpoint structure
        return {
            "success": True,
            "thread": thread_data
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating mini-agent thread: {str(e)}")

@router.get("/mini-agents/{session_id}", response_model=MiniAgentResponse)
async def get_mini_agent_threads(session_id: str):
    """Get all mini-agent threads for a session"""
    try:
        db = get_database()
        mini_agents_collection = db.mini_agent_threads
        messages_collection = db.mini_agent_messages
        
        threads = list(mini_agents_collection.find(
            {"sessionId": session_id},
            {"_id": 0}
        ))
        
        # Load messages for each thread
        for thread in threads:
            messages = list(messages_collection.find(
                {"threadId": thread["id"]},
                {"_id": 0}
            ).sort("createdAt", 1))
            
            # Convert datetime to ISO string for messages
            for message in messages:
                if "createdAt" in message:
                    message["createdAt"] = message["createdAt"].isoformat()
            
            thread["messages"] = messages
            
            # Convert thread createdAt
            if "createdAt" in thread:
                thread["createdAt"] = thread["createdAt"].isoformat()
        
        return MiniAgentResponse(threads=threads)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching mini-agent threads: {str(e)}")

@router.post("/mini-agents/{thread_id}/messages")
async def add_mini_agent_message(thread_id: str, request: AddMiniAgentMessageRequest):
    """Add a message to a mini-agent thread"""
    try:
        # For now, just return success without database storage
        # This allows testing of the API endpoint structure
        user_message = {
            "threadId": thread_id,
            "sender": "user",
            "text": request.text,
            "createdAt": datetime.utcnow().isoformat()
        }
        
        # Simple AI response for testing
        ai_response = f"I understand you're asking about: '{request.text}'. This is a test response from the mini-agent."
        
        return {
            "success": True,
            "userMessage": user_message,
            "aiMessage": {
                "threadId": thread_id,
                "sender": "ai", 
                "text": ai_response,
                "createdAt": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding message: {str(e)}")

@router.post("/share-conversation")
async def share_conversation(request: ShareConversationRequest):
    """Share a conversation with optional highlights"""
    try:
        db = get_database()
        
        # Get conversation context
        messages = list(db.messages.find(
            {"threadId": request.threadId}
        ).sort("createdAt", 1))
        
        # Build conversation context
        conversation_history = []
        for msg in messages:
            conversation_history.append(f"{msg['sender']}: {msg['text']}")
        
        # Create shareable conversation data
        share_data = {
            "threadId": request.threadId,
            "conversation": conversation_history,
            "highlights": request.highlights if hasattr(request, 'highlights') else [],
            "sharedAt": datetime.utcnow().isoformat()
        }
        
        return {"success": True, "data": share_data}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sharing conversation: {str(e)}")