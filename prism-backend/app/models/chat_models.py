from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class Message(BaseModel):
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

# INPUT: What the user sends us
class ChatRequest(BaseModel):
    message: str
    user_email: str
    session_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None

# OUTPUT: What we send back
class ChatResponse(BaseModel):
    reply: str
    intent: str
    success: bool = True
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    debug_info: Optional[dict] = None