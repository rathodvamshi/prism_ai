from pinecone import Pinecone, ServerlessSpec
try:
    from fastembed import TextEmbedding
except ImportError:
    print("Warning: fastembed not installed, memory features may be limited")
    TextEmbedding = None
from app.config import settings
import uuid
from datetime import datetime
import hashlib



# ------------------------------------------------------
# 1. Initialize Pinecone (v3 API) with error handling
# ------------------------------------------------------
import logging

logger = logging.getLogger(__name__)

def create_pinecone_client():
    """Create Pinecone client with error handling"""
    try:
        if not settings.PINECONE_API_KEY:
            logger.warning("Pinecone API key not configured")
            return None, None
        
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index("prism-memory")
        return pc, index
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {e}")
        return None, None

pc, index = create_pinecone_client()


# ------------------------------------------------------
# 2. Initialize Embedding Model (FastEmbed)
# ------------------------------------------------------
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5") if TextEmbedding else None


# ------------------------------------------------------
# Generate Embeddings
# ------------------------------------------------------
async def get_embedding(text: str):
    """
    Converts text into a dense embedding vector using FastEmbed.
    Ensures the returned vector is a Python list (not numpy array).
    """
    if not embedding_model:
        # Return a dummy embedding if TextEmbedding is not available
        return [0.0] * 384  # Standard embedding size
    vectors = list(embedding_model.embed([text]))
    return vectors[0].tolist()   # Convert NumPy → Python list


# ------------------------------------------------------
# Save Memory to Pinecone
# ------------------------------------------------------
def _deterministic_memory_id(user_id: str, text: str, memory_type: str) -> str:
    """Create a deterministic ID for a memory using a stable hash.
    Ensures upserts overwrite duplicates instead of creating new vectors.
    """
    norm = f"{user_id}|{memory_type}|{text.strip().lower()}".encode("utf-8")
    return hashlib.sha1(norm).hexdigest()  # Pinecone id as hex string


async def save_long_term_memory(user_id: str, text: str, memory_type: str = "fact"):
    """Saves or updates a memory vector in Pinecone with deterministic IDs."""
    if not text or not text.strip():
        return
    
    if not index:
        logger.warning("Pinecone not available, skipping memory save")
        return

    vector = await get_embedding(text)
    memory_id = _deterministic_memory_id(user_id, text, memory_type)

    try:
        index.upsert(
            vectors=[
                {
                    "id": memory_id,
                    "values": vector,
                    "metadata": {
                        "user_id": user_id,
                        "text": text,
                        "type": memory_type,
                        "timestamp": str(datetime.now())
                    }
                }
            ]
        )
        logger.info(f"✅ Memory upserted to Pinecone: {text}")
    except Exception as e:
        logger.error(f"Failed to save memory to Pinecone: {e}")


async def save_user_profile_memory(user_id: str, profile_data: dict):
    """
    Saves comprehensive user profile information to long-term memory.
    """
    # Save individual profile elements for better retrieval
    if profile_data.get("username"):
        await save_long_term_memory(user_id, f"User's name is {profile_data['username']}", "profile")
    
    if profile_data.get("hobby") and len(profile_data["hobby"]) > 0:
        hobbies_str = ", ".join(profile_data["hobby"])
        await save_long_term_memory(user_id, f"User enjoys {hobbies_str} as hobbies", "profile")
    
    if profile_data.get("role"):
        await save_long_term_memory(user_id, f"User works as a {profile_data['role']}", "profile")
    
    if profile_data.get("interests") and len(profile_data["interests"]) > 0:
        interests_text = ", ".join(profile_data["interests"])
        await save_long_term_memory(user_id, f"User is interested in: {interests_text}", "profile")
    
    if profile_data.get("responseStyle"):
        await save_long_term_memory(user_id, f"User prefers {profile_data['responseStyle']} communication style", "profile")
    
    # Save comprehensive profile summary
    profile_summary = f"User Profile Summary: {profile_data.get('username', 'User')}"
    if profile_data.get("role"):
        profile_summary += f" is a {profile_data['role']}"
    if profile_data.get("hobby") and len(profile_data["hobby"]) > 0:
        hobbies_str = ", ".join(profile_data["hobby"][:3])  # Limit to first 3 for summary
        profile_summary += f" who enjoys {hobbies_str}"
    if profile_data.get("interests"):
        profile_summary += f" and is interested in {', '.join(profile_data['interests'][:3])}"
    
    await save_long_term_memory(user_id, profile_summary, "profile")


# ------------------------------------------------------
# Retrieve Relevant Memories
# ------------------------------------------------------
async def retrieve_long_term_memory(user_id: str, query: str, top_k: int = 3):
    """
    Retrieves the top-k most relevant memories for a user.
    Uses semantic search (vector similarity).
    """
    if not index:
        logger.warning("Pinecone not available, returning empty memories")
        return []
    
    try:
        vector = await get_embedding(query)

        results = index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter={"user_id": user_id}   # Only load this user's memories
        )

        memories = []
        if results and hasattr(results, "matches"):
            for match in results.matches:
                if "text" in match.metadata:
                    memories.append(match.metadata["text"])

        return memories
    except Exception as e:
        logger.error(f"Failed to retrieve memories from Pinecone: {e}")
        return []
