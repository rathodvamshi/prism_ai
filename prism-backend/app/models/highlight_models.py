from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class HighlightData(BaseModel):
    highlightId: str
    userId: str
    sessionId: str
    messageId: str
    startIndex: int
    endIndex: int
    color: str
    createdAt: datetime
    text: str
    note: Optional[str] = None

class CreateHighlightRequest(BaseModel):
    userId: str
    sessionId: str
    messageId: str
    startIndex: int
    endIndex: int
    color: str
    text: str
    note: Optional[str] = None

class MiniAgentMessageData(BaseModel):
    threadId: str
    sender: str  # "user" or "ai"
    text: str
    createdAt: datetime

class MiniAgentThreadData(BaseModel):
    id: str
    sessionId: str
    messageId: str
    title: str
    createdAt: datetime
    selectedText: str
    messages: List[MiniAgentMessageData] = []

class CreateMiniAgentThreadRequest(BaseModel):
    sessionId: str
    messageId: str
    selectedText: str
    title: Optional[str] = None

class AddMiniAgentMessageRequest(BaseModel):
    threadId: str
    text: str

class ShareConversationRequest(BaseModel):
    sessionId: str
    includeHighlights: bool = False

class HighlightResponse(BaseModel):
    highlights: List[HighlightData]
    success: bool = True

class MiniAgentResponse(BaseModel):
    threads: List[MiniAgentThreadData]
    success: bool = True