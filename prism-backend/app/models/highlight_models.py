from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime

class HighlightData(BaseModel):
    highlightId: str
    userId: str
    sessionId: str  # Also known as thread_id
    messageId: str
    startIndex: int  # Absolute character offset (inclusive)
    endIndex: int    # Absolute character offset (exclusive)
    color: str
    text: str        # The actual highlighted substring
    messageHash: str # SHA256 checksum of original message for drift detection
    createdAt: datetime
    note: Optional[str] = None

class CreateHighlightRequest(BaseModel):
    userId: str
    sessionId: str
    messageId: str
    startIndex: int
    endIndex: int
    color: str
    text: str
    messageText: str  # Full message text for validation (not stored, used for hash generation)
    note: Optional[str] = None
    
    @field_validator('startIndex', 'endIndex')
    @classmethod
    def validate_indexes(cls, v):
        """Ensure indexes are non-negative"""
        if v < 0:
            raise ValueError('Indexes must be non-negative')
        return v

class MiniAgentMessageData(BaseModel):
    threadId: Optional[str] = None
    id: Optional[str] = None  # ✅ Frontend needs id field
    sender: Optional[str] = None  # "user" or "ai" (legacy)
    role: Optional[str] = None  # "user" or "assistant" (frontend standard)
    text: Optional[str] = None  # Legacy field
    content: Optional[str] = None  # Frontend standard field
    createdAt: Optional[datetime] = None
    timestamp: Optional[str] = None  # Frontend format

class MiniAgentThreadData(BaseModel):
    id: str
    sessionId: str
    messageId: str
    title: str
    createdAt: datetime
    selectedText: str
    messages: List[MiniAgentMessageData] = []
    hasConversation: bool = False  # ✅ Frontend needs this for icon display
    agentId: Optional[str] = None  # ✅ Some frontend code expects agentId instead of id

class CreateMiniAgentThreadRequest(BaseModel):
    sessionId: str
    messageId: str
    selectedText: str
    title: Optional[str] = None

class AddMiniAgentMessageRequest(BaseModel):
    text: str
    message_id: Optional[str] = None  # Message this question refers to

class UpdateMiniAgentSnippetRequest(BaseModel):
    selectedText: str

class ShareConversationRequest(BaseModel):
    sessionId: str
    includeHighlights: bool = False

class HighlightResponse(BaseModel):
    highlights: List[HighlightData]
    success: bool = True

class MiniAgentResponse(BaseModel):
    miniAgents: List[MiniAgentThreadData]
    success: bool = True