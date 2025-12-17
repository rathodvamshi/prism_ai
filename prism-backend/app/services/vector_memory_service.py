"""
🧠 VECTOR MEMORY (Pinecone)

For each user:
- Convert important messages → embeddings
- Store with namespace = userId to prevent mixing
- Enable semantic search and intelligent recall

🟢 Rule: Pinecone uses userId namespace, so no mixing between users
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from fastembed import TextEmbedding
from pinecone import Pinecone, ServerlessSpec
from app.config import settings
from app.models.perfect_models import PineconeMetadata
import logging

logger = logging.getLogger(__name__)

# ☁️ Cloud-Native Pinecone Configuration
# Supports both serverless (recommended) and pod-based indexes

# Initialize Pinecone conditionally
pc = None
try:
    if settings.PINECONE_API_KEY:
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        logger.info("✅ Pinecone initialized successfully")
    else:
        logger.warning("⚠️ Pinecone API key not provided, vector memory disabled")
except Exception as e:
    logger.error(f"❌ Failed to initialize Pinecone: {e}")
    pc = None

# Initialize FastEmbed for embeddings (local, fast, free)
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

# Index configuration (cloud-native)
INDEX_NAME = settings.PINECONE_INDEX_NAME or "prism-memory"
VECTOR_DIMENSION = 384  # BAAI/bge-small-en-v1.5 dimension

class VectorMemoryService:
    """
    Perfect Vector Memory Service for PRISM AI.
    Each user gets their own namespace to prevent data mixing.
    """
    
    def __init__(self):
        self.index = None
        self._initialize_index()
    
    def _initialize_index(self):
        """☁️ Initialize or connect to Pinecone index (cloud-native)"""
        try:
            if pc is None:
                logger.warning("⚠️ Pinecone client not available, vector memory disabled")
                self.index = None
                return
                
            # Check if index exists
            existing_indexes = [index.name for index in pc.list_indexes()]
            
            if INDEX_NAME not in existing_indexes:
                logger.info(f"🚀 Creating Pinecone index: {INDEX_NAME}")
                
                # ☁️ Cloud-Native: Use serverless by default (better for cloud deployment)
                index_type = getattr(settings, "PINECONE_INDEX_TYPE", "serverless").lower()
                
                if index_type == "serverless":
                    # Serverless spec (recommended for cloud - AWS/GCP)
                    environment = getattr(settings, "PINECONE_ENVIRONMENT", "us-east-1") or "us-east-1"
                    logger.info(f"☁️ Creating serverless index in {environment}")
                    pc.create_index(
                        name=INDEX_NAME,
                        dimension=VECTOR_DIMENSION,
                        metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region=environment)
                    )
                else:
                    # Pod-based spec (legacy, for starter plans)
                    environment = getattr(settings, "PINECONE_ENVIRONMENT", "gcp-starter") or "gcp-starter"
                    logger.info(f"📦 Creating pod-based index in {environment}")
                    pc.create_index(
                        name=INDEX_NAME,
                        dimension=VECTOR_DIMENSION,
                        metric="cosine",
                        spec={
                            "pod": {
                                "environment": environment,
                                "pod_type": "starter"
                            }
                        }
                    )
            
            # Connect to index
            self.index = pc.Index(INDEX_NAME)
            logger.info(f"✅ Connected to Pinecone index: {INDEX_NAME}")
            print(f"[SUCCESS] Connected to Pinecone index: {INDEX_NAME}")
            
        except Exception as e:
            logger.error(f"❌ Pinecone initialization error: {e}")
            print(f"[ERROR] Pinecone initialization error: {e}")
            self.index = None
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using FastEmbed"""
        try:
            embeddings = list(embedding_model.embed([text]))
            return embeddings[0].tolist()  # Convert numpy array to list
        except Exception as e:
            print(f"[ERROR] Embedding generation error: {e}")
            return [0.0] * VECTOR_DIMENSION  # Return zero vector as fallback
    
    async def store_memory(
        self, 
        user_id: str, 
        text: str, 
        memory_type: str = "conversation",
        vector_id: Optional[str] = None
    ) -> bool:
        """
        Store user memory as vector embedding.
        
        Args:
            user_id: User identifier (used as namespace)
            text: Text to embed and store
            memory_type: Type of memory ("conversation", "preference", "context", "fact")
            vector_id: Optional custom vector ID
            
        Returns:
            bool: Success status
        """
        if not self.index:
            logger.warning("❌ Pinecone index not initialized, memory storage disabled")
            return False
        
        try:
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            # Generate vector ID if not provided
            if not vector_id:
                # Deterministic ID to prevent duplicates: userId + normalized text + type
                norm_text = " ".join(text.lower().split())[:1024]
                import hashlib
                digest = hashlib.md5(f"{user_id}:{memory_type}:{norm_text}".encode()).hexdigest()
                vector_id = f"mem_{digest}"
            
            # Prepare metadata
            metadata = PineconeMetadata(
                userId=user_id,
                text=text,
                type=memory_type,
                timestamp=datetime.utcnow()
            )
            
            # Store in Pinecone with user namespace
            self.index.upsert(
                vectors=[{
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata.dict()
                }],
                namespace=user_id  # 🟢 CRITICAL: Each user gets own namespace
            )
            
            print(f"[SUCCESS] Memory stored for user {user_id}: {text[:50]}...")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error storing memory: {e}")
            return False

    async def add_memory(self, user_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Backwards-compatible wrapper expected by some callers.
        Uses `metadata.get('type')` if provided to select memory_type.
        """
        memory_type = (metadata or {}).get("type", "conversation")
        return await self.store_memory(user_id=user_id, text=text, memory_type=memory_type)
    
    async def search_memories(
        self, 
        user_id: str, 
        query: str, 
        top_k: int = 5,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search user's memories using semantic similarity.
        
        Args:
            user_id: User identifier (namespace)
            query: Search query
            top_k: Number of results to return
            memory_type: Optional filter by memory type
            
        Returns:
            List of matching memories with metadata
        """
        if not self.index:
            print("❌ Pinecone index not initialized")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            # Build filter
            filter_dict = {}
            if memory_type:
                filter_dict["type"] = {"$eq": memory_type}
            
            # Search in user's namespace only
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                namespace=user_id,  # 🟢 CRITICAL: Search only user's data
                filter=filter_dict if filter_dict else None
            )
            
            # Format results with score filtering
            # 🧠 MEMORY HARDENING PROTOCOL - Fix 3: Score Filtering (>0.75)
            memories = []
            for match in results.matches:
                score = match.score if hasattr(match, "score") else 0.0
                # QUALITY CONTROL: Only accept memories with > 75% match confidence
                if score > 0.75:
                    memory = {
                        "id": match.id,
                        "text": match.metadata.get("text", ""),
                        "type": match.metadata.get("type", "unknown"),
                        "score": score,
                        "timestamp": match.metadata.get("timestamp", "")
                    }
                    memories.append(memory)
                else:
                    print(f"[Memory Hardening] Rejected memory with score {score:.3f} (below 0.75 threshold)")
            
            print(f"[SUCCESS] Found {len(memories)} high-quality memories (score > 0.75) for query: {query}")
            return memories
            
        except Exception as e:
            print(f"[ERROR] Error searching memories: {e}")
            return []
    
    async def get_user_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about user's stored memories"""
        if not self.index:
            return {"error": "Index not initialized"}
        
        try:
            # Get namespace stats
            stats = self.index.describe_index_stats()
            user_stats = stats.namespaces.get(user_id, {})
            
            return {
                "total_vectors": user_stats.get("vector_count", 0),
                "namespace": user_id,
                "index_fullness": stats.index_fullness
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def delete_user_memories(self, user_id: str) -> bool:
        """Delete all memories for a user"""
        if not self.index:
            return False
        
        try:
            # Delete entire namespace (all user's vectors)
            self.index.delete(delete_all=True, namespace=user_id)
            print(f"[SUCCESS] Deleted all memories for user: {user_id}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error deleting user memories: {e}")
            return False
    
    async def store_conversation_memory(self, user_id: str, messages: List[Dict[str, str]]) -> bool:
        """
        Store important parts of conversation as memory.
        Automatically extracts key information.
        """
        try:
            # Combine recent messages into context
            conversation_text = ""
            for msg in messages[-10:]:  # Last 10 messages
                role = msg.get("role", "")
                content = msg.get("content", "")
                conversation_text += f"{role}: {content}\n"
            
            # Store if conversation has meaningful content
            if len(conversation_text.strip()) > 20:
                await self.store_memory(
                    user_id=user_id,
                    text=conversation_text,
                    memory_type="conversation"
                )
                return True
            return False
            
        except Exception as e:
            print(f"[ERROR] Error storing conversation memory: {e}")
            return False
    
    async def extract_and_store_preferences(self, user_id: str, user_message: str) -> bool:
        """
        Extract preferences from user messages and store them.
        Examples: "I love biryani", "I prefer formal responses"
        """
        try:
            # Simple preference detection patterns
            preference_patterns = [
                "i love", "i like", "i enjoy", "i prefer", 
                "my favorite", "i hate", "i dislike", "i don't like"
            ]
            
            message_lower = user_message.lower()
            
            # Check if message contains preferences
            for pattern in preference_patterns:
                if pattern in message_lower:
                    await self.store_memory(
                        user_id=user_id,
                        text=user_message,
                        memory_type="preference"
                    )
                    print(f"[SUCCESS] Stored preference: {user_message[:50]}...")
                    return True
            
            return False
            
        except Exception as e:
            print(f"[ERROR] Error extracting preferences: {e}")
            return False
    
    async def get_relevant_context(self, user_id: str, current_query: str) -> str:
        """
        Get relevant context for current query from user's memory.
        This powers intelligent AI responses.
        """
        try:
            # Search for relevant memories
            memories = await self.search_memories(
                user_id=user_id,
                query=current_query,
                top_k=3
            )
            
            if not memories:
                return ""
            
            # Format context
            context_parts = []
            for memory in memories:
                if memory["score"] > 0.7:  # High similarity threshold
                    context_parts.append(f"Previous context: {memory['text']}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"[ERROR] Error getting relevant context: {e}")
            return ""

# Global instance - lazily initialized
vector_memory = None

def get_vector_memory():
    """Get or create the vector memory service instance"""
    global vector_memory
    if vector_memory is None:
        vector_memory = VectorMemoryService()
    return vector_memory

# 🎯 CONVENIENCE FUNCTIONS FOR EASY USE

async def store_user_memory(user_id: str, text: str, memory_type: str = "conversation") -> bool:
    """Simple function to store user memory"""
    vm = get_vector_memory()
    return await vm.store_memory(user_id, text, memory_type)

async def search_user_memories(user_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Simple function to search user memories"""
    vm = get_vector_memory()
    return await vm.search_memories(user_id, query, top_k)

async def get_ai_context_for_user(user_id: str, query: str) -> str:
    """Get relevant AI context for user query"""
    vm = get_vector_memory()
    return await vm.get_relevant_context(user_id, query)

async def process_user_message_for_memory(user_id: str, message: str):
    """Process user message and extract/store relevant memories"""
    vm = get_vector_memory()
    # Store preferences if detected
    await vm.extract_and_store_preferences(user_id, message)
    
    # Store as general conversation memory
    await vm.store_memory(user_id, message, "conversation")

# 📊 MEMORY ANALYTICS
async def get_memory_analytics() -> Dict[str, Any]:
    """Get overall memory system analytics"""
    try:
        vm = get_vector_memory()
        if not vm.index:
            return {"error": "Index not initialized"}
        
        stats = vm.index.describe_index_stats()
        
        return {
            "total_vectors": stats.total_vector_count,
            "index_fullness": stats.index_fullness,
            "dimension": VECTOR_DIMENSION,
            "total_namespaces": len(stats.namespaces) if stats.namespaces else 0
        }
        
    except Exception as e:
        return {"error": str(e)}