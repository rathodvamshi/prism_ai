"""
🚀 Part 13: Async Memory Background Tasks

Save memory writes AFTER response in background tasks.
Never block chat replies for memory operations!

Memory writes (slow):
- Neo4j graph relationships
- Pinecone vector embeddings
- Pending memory sync

Result: Faster chat replies (200ms vs 1s+)
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.advanced_memory_manager import AdvancedMemoryManager
from app.services.pending_memory_service import save_draft_memory

logger = logging.getLogger(__name__)


class MemoryBackgroundTasks:
    """
    Background task manager for async memory operations.
    🚀 Part 13: Do memory writes AFTER response, not during!
    """
    
    def __init__(self):
        self.memory_manager = AdvancedMemoryManager()
    
    async def save_conversation_memory(
        self,
        user_id: str,
        user_message: str,
        ai_response: str,
        session_id: Optional[str] = None
    ):
        """
        Save conversation to all memory systems in background.
        🚀 Part 13: Runs AFTER chat response is sent.
        """
        try:
            logger.info(f"💾 [BACKGROUND] Saving conversation memory for user: {user_id}")
            
            # 1. Save to MongoDB (fast, critical)
            try:
                await self.memory_manager.save_conversation(
                    user_id,
                    session_id or "default",
                    user_message,
                    ai_response
                )
                logger.info(f"✅ MongoDB conversation saved")
            except Exception as mongo_error:
                logger.error(f"❌ MongoDB save failed: {mongo_error}")
            
            # 2. Save to Neo4j (slow, can fail gracefully)
            try:
                await self._save_to_neo4j(user_id, user_message, ai_response)
            except Exception as neo4j_error:
                logger.warning(f"⚠️ Neo4j save failed (will retry via pending): {neo4j_error}")
                # Save as draft for later sync
                await save_draft_memory(
                    user_id=user_id,
                    memory_type="CONVERSATION",
                    value={"message": user_message, "response": ai_response},
                    source="neo4j_background",
                    targets=["neo4j"]
                )
            
            # 3. Save to Pinecone (slowest, optional)
            try:
                await self._save_to_pinecone(user_id, user_message, ai_response)
            except Exception as pinecone_error:
                logger.warning(f"⚠️ Pinecone save failed (skipping): {pinecone_error}")
                # Pinecone is optional, don't save as draft
            
            logger.info(f"✅ [BACKGROUND] Memory save completed for user: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ [BACKGROUND] Memory save error: {e}")
    
    async def _save_to_neo4j(self, user_id: str, message: str, response: str):
        """🚀 Part 13: Background Neo4j save"""
        try:
            # Extract and save relationships from message
            await self.memory_manager.neo4j_client.add_conversation_node(
                user_id,
                message,
                response
            )
            logger.info(f"✅ Neo4j conversation saved")
        except Exception as e:
            logger.error(f"Neo4j save error: {e}")
            raise  # Re-raise to trigger draft save
    
    async def _save_to_pinecone(self, user_id: str, message: str, response: str):
        """🚀 Part 13: Background Pinecone save"""
        try:
            combined_text = f"User: {message}\nAssistant: {response}"
            await self.memory_manager.add_vector_memory(user_id, combined_text)
            logger.info(f"✅ Pinecone vector saved")
        except Exception as e:
            logger.error(f"Pinecone save error: {e}")
            # Don't re-raise, Pinecone is optional
    
    async def update_user_context(
        self,
        user_id: str,
        context_updates: Dict[str, Any]
    ):
        """
        Update user context (interests, preferences) in background.
        🚀 Part 13: Runs AFTER chat response.
        """
        try:
            logger.info(f"💾 [BACKGROUND] Updating user context for: {user_id}")
            
            # Update interests
            if "interests" in context_updates:
                for interest in context_updates["interests"]:
                    try:
                        await self.memory_manager.add_graph_relationship(
                            user_id,
                            "INTERESTED_IN",
                            interest
                        )
                    except Exception as e:
                        logger.warning(f"Interest update failed: {e}")
            
            # Update preferences
            if "preferences" in context_updates:
                try:
                    await self.memory_manager.add_structured_memory(
                        user_id,
                        {
                            "type": "preference",
                            "value": context_updates["preferences"],
                            "updated_at": datetime.now().isoformat()
                        }
                    )
                except Exception as e:
                    logger.warning(f"Preference update failed: {e}")
            
            logger.info(f"✅ [BACKGROUND] Context update completed")
            
        except Exception as e:
            logger.error(f"❌ [BACKGROUND] Context update error: {e}")
    
    async def sync_pending_memories(self, user_id: Optional[str] = None):
        """
        Sync pending/draft memories to final destinations.
        🚀 Part 13: Background sync job.
        """
        try:
            logger.info(f"🔄 [BACKGROUND] Syncing pending memories...")
            
            from app.services.pending_memory_service import sync_pending_graph_memories
            
            await sync_pending_graph_memories(
                per_item_timeout_seconds=5.0,
                max_items=100
            )
            
            logger.info(f"✅ [BACKGROUND] Pending memories synced")
            
        except Exception as e:
            logger.error(f"❌ [BACKGROUND] Pending sync error: {e}")
    
    async def extract_and_save_entities(
        self,
        user_id: str,
        text: str
    ):
        """
        Extract entities from text and save to knowledge graph.
        🚀 Part 13: Background NLP/entity extraction.
        """
        try:
            logger.info(f"💾 [BACKGROUND] Extracting entities for user: {user_id}")
            
            # Simple keyword extraction (can be replaced with NLP)
            keywords = self._extract_keywords(text)
            
            for keyword in keywords:
                try:
                    await self.memory_manager.add_graph_relationship(
                        user_id,
                        "MENTIONED",
                        keyword
                    )
                except Exception as e:
                    logger.warning(f"Entity save failed for '{keyword}': {e}")
            
            logger.info(f"✅ [BACKGROUND] Entity extraction completed")
            
        except Exception as e:
            logger.error(f"❌ [BACKGROUND] Entity extraction error: {e}")
    
    def _extract_keywords(self, text: str) -> list:
        """Simple keyword extraction (replace with proper NLP if needed)"""
        # Remove common words and extract important ones
        common_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                       "have", "has", "had", "do", "does", "did", "will", "would", "could",
                       "should", "may", "might", "can", "to", "of", "in", "for", "on", "at",
                       "by", "with", "from", "as", "into", "through", "during", "before",
                       "after", "above", "below", "up", "down", "out", "off", "over", "under"}
        
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in common_words]
        
        # Return unique keywords (max 10)
        return list(set(keywords))[:10]


# Global instance
memory_background_tasks = MemoryBackgroundTasks()


# ========== HELPER FUNCTIONS FOR EASY USE ==========

async def save_memory_async(
    user_id: str,
    user_message: str,
    ai_response: str,
    session_id: Optional[str] = None
):
    """
    Convenience function to save memory in background.
    🚀 Part 13: Call this AFTER sending response to user.
    """
    await memory_background_tasks.save_conversation_memory(
        user_id,
        user_message,
        ai_response,
        session_id
    )


async def update_context_async(user_id: str, context_updates: Dict[str, Any]):
    """
    Convenience function to update context in background.
    🚀 Part 13: Call this AFTER sending response to user.
    """
    await memory_background_tasks.update_user_context(user_id, context_updates)


async def extract_entities_async(user_id: str, text: str):
    """
    Convenience function to extract entities in background.
    🚀 Part 13: Call this AFTER sending response to user.
    """
    await memory_background_tasks.extract_and_save_entities(user_id, text)
