"""
🛠️ PERFECT DATA STRUCTURE MODELS (Exactly as specified)

All models follow the baby-level simple structure with:
- Every user identified by email as primary unique identifier
- userId (MongoDB ObjectId) for internal linking
- Complete user separation guaranteed
- No duplicates allowed
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from enum import Enum

# 🔧 Custom ObjectId field for Pydantic
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, field=None, config=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        json_schema = handler(core_schema)
        json_schema.update(type="string")
        return json_schema

# 📌 USERS COLLECTION MODEL
class UserModel(BaseModel):
    """
    Stores account profile data.
    🟢 Rule 1: Every user → use their email as primary unique identifier
    """
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    email: EmailStr  # Primary unique identifier
    name: str
    role: Optional[str] = "user"
    hobbies: List[str] = []
    interests: List[str] = []
    responseStyle: Optional[str] = "friendly"
    avatar: Optional[str] = ""
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# 📌 MESSAGE MODEL (for sessions)
class MessageModel(BaseModel):
    """Individual message in a chat session"""
    role: str  # "user" or "assistant"
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# 📌 SESSIONS COLLECTION MODEL  
class SessionModel(BaseModel):
    """
    Chat sessions grouped by sessionId.
    🟢 Rule 2: In every database, store everything under userId
    🟢 MongoDB is the single source of truth - no LocalStorage dependencies
    """
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    sessionId: str  # Unique session identifier (also stored as chat_id for compatibility)
    userId: PyObjectId  # Link to user (NEVER store without userId)
    title: str = "New Chat"  # Session title (can be renamed)
    messages: List[MessageModel] = []
    isPinned: bool = False  # Pin status stored in MongoDB
    isSaved: bool = False  # Save status stored in MongoDB
    isDeleted: bool = False  # Soft delete flag
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# 📌 TASK STATUS ENUM
class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# 📌 TASKS COLLECTION MODEL
class TaskModel(BaseModel):
    """
    Store tasks separately for performance.
    🟢 Rule 3: NEVER store tasks without linking to userId
    """
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    taskId: str  # Unique task identifier (e.g., "T123")
    userId: PyObjectId  # Link to user (NEVER store without userId)
    title: str
    description: Optional[str] = ""
    status: TaskStatus = TaskStatus.PENDING
    email_status: str = "queued"  # queued, sent, failed, retrying
    email_retry_count: int = 0
    email_last_error: Optional[str] = None
    email_sent_at: Optional[datetime] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    completedAt: Optional[datetime] = None
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# 📌 MEMORY FACT MODEL
class MemoryFact(BaseModel):
    """Individual memory fact"""
    type: str  # "hobby", "interest", "preference", "context"
    value: str
    confidence: float = 1.0  # How confident we are in this fact
    createdAt: datetime = Field(default_factory=datetime.utcnow)

# 📌 MEMORY COLLECTION MODEL (structured memory)
class MemoryModel(BaseModel):
    """
    Structured memory storage for each user.
    🟢 Rule: Always check before inserting to avoid duplicates
    """
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    userId: PyObjectId  # Link to user (NEVER store without userId)
    facts: List[MemoryFact] = []
    preferences: Dict[str, Any] = {}  # {"responseStyle": "friendly"}
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# 🎯 REQUEST/RESPONSE MODELS FOR API

class CreateUserRequest(BaseModel):
    """Request to create a new user"""
    email: EmailStr
    name: str
    role: Optional[str] = "user"
    hobbies: List[str] = []
    interests: List[str] = []
    responseStyle: Optional[str] = "friendly"

class SendMessageRequest(BaseModel):
    """Request to send a message in a session"""
    userId: str
    sessionId: str
    message: str

class CreateTaskRequest(BaseModel):
    """Request to create a new task"""
    userId: str
    title: str
    description: Optional[str] = ""

class AddMemoryRequest(BaseModel):
    """Request to add memory fact"""
    userId: str
    type: str  # "hobby", "interest", "preference", "context"
    value: str
    confidence: Optional[float] = 1.0

# 🧠 PINECONE METADATA MODEL
class PineconeMetadata(BaseModel):
    """
    Metadata structure for Pinecone vectors.
    🟢 Rule: namespace = userId to prevent mixing
    """
    userId: str  # ALWAYS include userId
    text: str    # Original text that was embedded
    type: str    # "preference", "context", "memory"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# 🔗 NEO4J NODE MODELS  
class UserNode(BaseModel):
    """User node in Neo4j graph"""
    id: str  # userId
    email: str
    name: str

class InterestNode(BaseModel):
    """Interest/Hobby node in Neo4j graph"""
    name: str
    category: str  # "hobby", "interest", "skill"

class TaskNode(BaseModel):
    """Task node in Neo4j graph"""  
    taskId: str
    title: str
    status: str

# 🎯 BABY-LEVEL SUMMARY TYPES
class UserSummary(BaseModel):
    """Simple user summary for responses"""
    userId: str
    email: str
    name: str
    totalTasks: int
    completedTasks: int
    interests: List[str]
    hobbies: List[str]
    responseStyle: str

class SessionSummary(BaseModel):
    """Simple session summary"""
    sessionId: str
    messageCount: int
    lastMessage: str
    updatedAt: datetime