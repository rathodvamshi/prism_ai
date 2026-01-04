"""
🧠 MEMORY CONSOLIDATION SERVICE
===============================

This service is responsible for "sleeping on it" - taking short-term 
session memories and consolidating them into long-term knowledge graph.

Strong Features:
1. Session Analysis: Reads recent chat history
2. Fact Extraction: Identifies new entities and relationships
3. Graph Update: Commits permanent knowledge to Neo4j
"""

import logging
import re
from typing import List, Dict, Any
from datetime import datetime
from app.db.mongo_client import sessions_collection
from app.db.neo4j_client import graph_memory

logger = logging.getLogger(__name__)

class MemoryConsolidationService:
    """
    Service to consolidate short-term memory into long-term graph knowledge.
    """
    
    async def consolidate_user_memory(self, user_id: str, session_limit: int = 5) -> Dict[str, Any]:
        """
        Main entry point: Consolidate recent sessions for a user.
        """
        logger.info(f"🧠 Starting memory consolidation for user: {user_id}")
        
        # 1. Fetch recent sessions
        sessions = await self._fetch_recent_sessions(user_id, session_limit)
        if not sessions:
            return {"status": "no_sessions", "facts_extracted": 0}
            
        # 2. Extract facts from conversations
        new_facts = self._extract_facts_from_sessions(sessions)
        
        # 3. Commit to Neo4j
        committed_count = 0
        for fact in new_facts:
            success = await self._commit_fact_to_graph(user_id, fact)
            if success:
                committed_count += 1
                
        logger.info(f"✅ Consolidated {committed_count} new facts for user {user_id}")
        
        return {
            "status": "success",
            "sessions_analyzed": len(sessions),
            "facts_extracted": len(new_facts),
            "facts_committed": committed_count,
            "details": new_facts
        }
    
    async def _fetch_recent_sessions(self, user_id: str, limit: int) -> List[Dict]:
        """Fetch recent sessions from MongoDB"""
        try:
            from bson import ObjectId
            cursor = sessions_collection.find(
                {"userId": ObjectId(user_id)}
            ).sort("updatedAt", -1).limit(limit)
            
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"❌ Error fetching sessions: {e}")
            return []

    def _extract_facts_from_sessions(self, sessions: List[Dict]) -> List[Dict]:
        """
        Extract structured facts from raw conversation text.
        TODO: Replace regex with LLM for "Stronger" extraction.
        """
        facts = []
        
        # Patterns for extraction
        patterns = [
            (r"i am learning ([\w\s]+)", "LEARNING"),
            (r"i work with ([\w\s]+)", "WORKS_WITH"),
            (r"i live in ([\w\s]+)", "LIVES_IN"),
            (r"my goal is ([\w\s]+)", "HAS_GOAL"),
            (r"i use ([\w\s]+)", "USES_TECHNOLOGY")
        ]
        
        for session in sessions:
            for msg in session.get("messages", []):
                if msg.get("role") == "user":
                    text = msg.get("text", "").lower()
                    
                    for pattern, rel_type in patterns:
                        match = re.search(pattern, text)
                        if match:
                            target = match.group(1).strip()
                            # Basic cleanup
                            if len(target) > 2 and len(target) < 50:
                                facts.append({
                                    "relationship": rel_type,
                                    "target": target.title(),
                                    "source_text": text
                                })
                                
        return facts

    async def _commit_fact_to_graph(self, user_id: str, fact: Dict) -> bool:
        """Commit a single fact to Neo4j"""
        try:
            # Use the existing dynamic relationship method
            return await graph_memory.add_dynamic_relationship(
                user_id=user_id,
                target=fact["target"],
                relationship_type=fact["relationship"],
                target_label="Entity"
            )
        except Exception as e:
            logger.error(f"❌ Error committing fact to graph: {e}")
            return False

# Global instance
consolidation_service = MemoryConsolidationService()
