"""
📊 MEMORY CONFIDENCE - Scoring & Strengthening System
=====================================================

This module provides confidence scoring, memory strengthening, and
intelligent memory prioritization.

Key Features:
- Confidence scoring for each memory item (0.0 - 1.0)
- Source-based confidence (explicit > inferred > guessed)
- Verification tracking (confirmed memories score higher)
- Time-based decay for stale memories
- Importance classification (permanent vs session)
- Memory strengthening through re-confirmation

Usage:
    from app.services.memory_confidence import MemoryConfidence, memory_confidence
    
    # Score a new memory
    score = memory_confidence.calculate_score(memory_item)
    
    # Strengthen a confirmed memory
    memory_confidence.strengthen(user_id, memory_id)
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class MemorySource(Enum):
    """Source of memory - affects confidence"""
    USER_EXPLICIT = "user_explicit"      # User directly stated (highest confidence)
    USER_CONFIRMED = "user_confirmed"    # User confirmed when asked
    AI_EXTRACTED = "ai_extracted"        # Extracted by AI from conversation
    INFERRED = "inferred"                # Logically inferred from context
    SYSTEM = "system"                    # System-generated metadata
    UNKNOWN = "unknown"                  # Source unknown (lowest confidence)


class MemoryImportance(Enum):
    """Importance level - affects retention"""
    CRITICAL = "critical"      # Never forget (name, core identity)
    HIGH = "high"              # Important long-term (preferences, projects)
    MEDIUM = "medium"          # Useful context (recent topics, interests)
    LOW = "low"                # Temporary context (session-specific)
    EPHEMERAL = "ephemeral"    # Very short-term (current task context)


class MemoryCategory(Enum):
    """Category of memory - for classification"""
    IDENTITY = "identity"           # Name, age, occupation
    LOCATION = "location"           # Where user lives/works
    PREFERENCE = "preference"       # Likes, dislikes, favorites
    RELATIONSHIP = "relationship"   # Family, friends, colleagues
    PROJECT = "project"             # Work projects, goals
    INTEREST = "interest"           # Hobbies, topics of interest
    SKILL = "skill"                 # Abilities, expertise
    CONTEXT = "context"             # Conversation context
    BEHAVIOR = "behavior"           # Communication preferences
    TEMPORAL = "temporal"           # Time-based info (schedule, events)


@dataclass
class MemoryMetadata:
    """Metadata for a memory item"""
    source: MemorySource = MemorySource.UNKNOWN
    importance: MemoryImportance = MemoryImportance.MEDIUM
    category: MemoryCategory = MemoryCategory.CONTEXT
    confidence: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    verification_count: int = 0
    decay_rate: float = 0.01  # Per day decay
    version: int = 1


class MemoryConfidence:
    """
    📊 MEMORY CONFIDENCE SYSTEM
    
    Provides intelligent scoring and strengthening for memories.
    Higher confidence memories are prioritized in recall.
    """
    
    def __init__(self):
        # Base confidence scores by source
        self.SOURCE_BASE_CONFIDENCE = {
            MemorySource.USER_EXPLICIT: 0.95,
            MemorySource.USER_CONFIRMED: 0.90,
            MemorySource.AI_EXTRACTED: 0.70,
            MemorySource.INFERRED: 0.50,
            MemorySource.SYSTEM: 0.80,
            MemorySource.UNKNOWN: 0.30,
        }
        
        # Importance-based retention (days before decay starts)
        self.IMPORTANCE_RETENTION = {
            MemoryImportance.CRITICAL: float('inf'),  # Never decays
            MemoryImportance.HIGH: 365,               # 1 year
            MemoryImportance.MEDIUM: 90,              # 3 months
            MemoryImportance.LOW: 30,                 # 1 month
            MemoryImportance.EPHEMERAL: 1,            # 1 day
        }
        
        # Category to importance mapping (defaults)
        self.CATEGORY_IMPORTANCE = {
            MemoryCategory.IDENTITY: MemoryImportance.CRITICAL,
            MemoryCategory.LOCATION: MemoryImportance.HIGH,
            MemoryCategory.PREFERENCE: MemoryImportance.HIGH,
            MemoryCategory.RELATIONSHIP: MemoryImportance.HIGH,
            MemoryCategory.PROJECT: MemoryImportance.MEDIUM,
            MemoryCategory.INTEREST: MemoryImportance.MEDIUM,
            MemoryCategory.SKILL: MemoryImportance.MEDIUM,
            MemoryCategory.CONTEXT: MemoryImportance.LOW,
            MemoryCategory.BEHAVIOR: MemoryImportance.HIGH,
            MemoryCategory.TEMPORAL: MemoryImportance.LOW,
        }
        
        # Keywords for category detection
        self.CATEGORY_KEYWORDS = {
            MemoryCategory.IDENTITY: [
                "name", "called", "age", "years old", "born", "birthday",
                "occupation", "job", "work as", "profession"
            ],
            MemoryCategory.LOCATION: [
                "live", "from", "city", "country", "based in", "located",
                "address", "home", "office", "timezone"
            ],
            MemoryCategory.PREFERENCE: [
                "like", "love", "prefer", "favorite", "enjoy", "hate",
                "dislike", "don't like", "avoid", "allergic"
            ],
            MemoryCategory.RELATIONSHIP: [
                "wife", "husband", "spouse", "partner", "friend", "family",
                "mother", "father", "brother", "sister", "child", "kid",
                "colleague", "boss", "team"
            ],
            MemoryCategory.PROJECT: [
                "project", "working on", "building", "creating", "developing",
                "goal", "objective", "deadline", "milestone"
            ],
            MemoryCategory.INTEREST: [
                "interested in", "hobby", "passionate about", "into",
                "curious about", "learning", "studying"
            ],
            MemoryCategory.SKILL: [
                "know how", "can do", "expert in", "skilled at", "experience with",
                "proficient", "fluent", "certified"
            ],
            MemoryCategory.BEHAVIOR: [
                "prefer to communicate", "response style", "format",
                "concise", "detailed", "formal", "casual"
            ],
        }
        
        logger.info("📊 MemoryConfidence system initialized")
    
    def get_confidence_from_source(self, source: MemorySource) -> float:
        """
        Get base confidence score for a memory source
        
        Args:
            source: The MemorySource enum value
            
        Returns:
            Base confidence score (0.0 - 1.0)
        """
        return self.SOURCE_BASE_CONFIDENCE.get(source, 0.5)
    
    def calculate_score(
        self,
        memory: Dict[str, Any],
        metadata: Optional[MemoryMetadata] = None
    ) -> float:
        """
        Calculate confidence score for a memory item
        
        Factors:
        - Source reliability
        - Age (with decay)
        - Verification count
        - Access frequency
        - Content quality
        
        Returns:
            Float between 0.0 and 1.0
        """
        if metadata is None:
            metadata = self._extract_metadata(memory)
        
        # 1. Base confidence from source
        base_score = self.SOURCE_BASE_CONFIDENCE.get(metadata.source, 0.5)
        
        # 2. Verification bonus (each verification adds 0.05, max 0.2)
        verification_bonus = min(0.2, metadata.verification_count * 0.05)
        
        # 3. Recency bonus (recently accessed memories score higher)
        recency_bonus = self._calculate_recency_bonus(metadata.last_accessed)
        
        # 4. Access frequency bonus (frequently accessed = important)
        access_bonus = min(0.1, math.log1p(metadata.access_count) * 0.02)
        
        # 5. Age decay (unless critical importance)
        decay_penalty = self._calculate_decay_penalty(metadata)
        
        # 6. Content quality score
        content_quality = self._assess_content_quality(memory)
        
        # Combine factors
        raw_score = (
            base_score * 0.4 +
            verification_bonus +
            recency_bonus * 0.1 +
            access_bonus +
            content_quality * 0.2
        ) - decay_penalty
        
        # Clamp to [0.0, 1.0]
        final_score = max(0.0, min(1.0, raw_score))
        
        logger.debug(
            f"📊 Score calculated: {final_score:.3f} "
            f"(base={base_score:.2f}, verify={verification_bonus:.2f}, "
            f"recency={recency_bonus:.2f}, decay={decay_penalty:.2f})"
        )
        
        return final_score
    
    def _calculate_recency_bonus(self, last_accessed: datetime) -> float:
        """Calculate bonus based on recency of access"""
        age_hours = (datetime.utcnow() - last_accessed).total_seconds() / 3600
        
        if age_hours < 1:
            return 0.15  # Very recent
        elif age_hours < 24:
            return 0.10  # Today
        elif age_hours < 168:  # 1 week
            return 0.05
        else:
            return 0.0
    
    def _calculate_decay_penalty(self, metadata: MemoryMetadata) -> float:
        """Calculate decay penalty based on age and importance"""
        if metadata.importance == MemoryImportance.CRITICAL:
            return 0.0  # No decay for critical memories
        
        retention_days = self.IMPORTANCE_RETENTION.get(metadata.importance, 90)
        age_days = (datetime.utcnow() - metadata.created_at).days
        
        if age_days <= retention_days:
            return 0.0  # Within retention period
        
        # Calculate decay after retention period
        days_past_retention = age_days - retention_days
        decay = days_past_retention * metadata.decay_rate
        
        return min(0.5, decay)  # Max 50% penalty
    
    def _assess_content_quality(self, memory: Dict[str, Any]) -> float:
        """Assess quality of memory content"""
        score = 0.5  # Base score
        
        # Get text content
        text = memory.get("text") or memory.get("value") or memory.get("content", "")
        if isinstance(text, str):
            # Length check (too short = low quality)
            if len(text) < 5:
                score -= 0.2
            elif len(text) > 20:
                score += 0.1
            
            # Specificity (contains proper nouns, numbers = more specific)
            import re
            if re.search(r'\b[A-Z][a-z]+\b', text):  # Proper nouns
                score += 0.1
            if re.search(r'\b\d+\b', text):  # Numbers
                score += 0.05
        
        # Has metadata = higher quality
        if memory.get("type") or memory.get("category"):
            score += 0.1
        
        if memory.get("source"):
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _extract_metadata(self, memory: Dict[str, Any]) -> MemoryMetadata:
        """Extract or create metadata from memory dict"""
        # Determine source
        source_str = memory.get("source", "unknown").lower()
        source = MemorySource.UNKNOWN
        for s in MemorySource:
            if s.value in source_str:
                source = s
                break
        
        # Determine category from content
        category = self.detect_category(memory)
        
        # Determine importance from category
        importance = self.CATEGORY_IMPORTANCE.get(category, MemoryImportance.MEDIUM)
        
        # Parse timestamps
        created_at = memory.get("created_at") or memory.get("timestamp")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except:
                created_at = datetime.utcnow()
        elif created_at is None:
            created_at = datetime.utcnow()
        
        return MemoryMetadata(
            source=source,
            importance=importance,
            category=category,
            confidence=memory.get("confidence", 0.5),
            created_at=created_at,
            updated_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            access_count=memory.get("access_count", 0),
            verification_count=memory.get("verification_count", 0),
            version=memory.get("version", 1)
        )
    
    def detect_category(self, memory: Dict[str, Any]) -> MemoryCategory:
        """Detect memory category from content"""
        # Check if category is already set
        if "category" in memory:
            cat_str = memory["category"].lower()
            for cat in MemoryCategory:
                if cat.value in cat_str:
                    return cat
        
        # Detect from content
        text = str(memory.get("text") or memory.get("value") or "").lower()
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        
        return MemoryCategory.CONTEXT  # Default
    
    def detect_importance(self, memory: Dict[str, Any]) -> MemoryImportance:
        """Detect importance level of a memory"""
        category = self.detect_category(memory)
        return self.CATEGORY_IMPORTANCE.get(category, MemoryImportance.MEDIUM)
    
    def apply_time_decay(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply time-based decay to a memory's confidence
        
        Args:
            memory: The memory to apply decay to
            
        Returns:
            Updated memory with decayed confidence
        """
        updated = memory.copy()
        metadata = self._extract_metadata(memory)
        
        # Critical memories never decay
        if metadata.importance == MemoryImportance.CRITICAL:
            return updated
        
        # Calculate age in days
        age_days = (datetime.utcnow() - metadata.created_at).days
        
        # Get retention period for this importance level
        retention_days = self.IMPORTANCE_RETENTION.get(metadata.importance, 90)
        
        # No decay within retention period
        if age_days <= retention_days:
            return updated
        
        # Calculate decay (exponential decay after retention period)
        days_past_retention = age_days - retention_days
        decay_factor = 0.01  # 1% per day past retention
        
        # Higher importance = slower decay
        if metadata.importance == MemoryImportance.HIGH:
            decay_factor = 0.005
        elif metadata.importance == MemoryImportance.LOW:
            decay_factor = 0.02
        elif metadata.importance == MemoryImportance.EPHEMERAL:
            decay_factor = 0.1
        
        current_confidence = memory.get("confidence", 0.5)
        decay_amount = days_past_retention * decay_factor
        new_confidence = max(0.1, current_confidence - decay_amount)
        
        updated["confidence"] = new_confidence
        updated["decay_applied"] = True
        updated["decay_calculated_at"] = datetime.utcnow().isoformat()
        
        logger.debug(
            f"📉 Time decay applied: {current_confidence:.3f} → {new_confidence:.3f} "
            f"(age={age_days}d, retention={retention_days}d)"
        )
        
        return updated
    
    def detect_source(self, memory: Dict[str, Any], context: Optional[Dict] = None) -> MemorySource:
        """Detect the source of a memory"""
        # Explicit indicators
        source_str = str(memory.get("source", "")).lower()
        
        if "explicit" in source_str or "stated" in source_str:
            return MemorySource.USER_EXPLICIT
        if "confirmed" in source_str or "verified" in source_str:
            return MemorySource.USER_CONFIRMED
        if "extracted" in source_str or "ai" in source_str:
            return MemorySource.AI_EXTRACTED
        if "inferred" in source_str or "guessed" in source_str:
            return MemorySource.INFERRED
        if "system" in source_str:
            return MemorySource.SYSTEM
        
        # Context-based detection
        if context:
            if context.get("is_direct_statement"):
                return MemorySource.USER_EXPLICIT
            if context.get("is_confirmation"):
                return MemorySource.USER_CONFIRMED
        
        return MemorySource.UNKNOWN
    
    def strengthen(
        self,
        memory: Dict[str, Any],
        verification_type: str = "access"
    ) -> Dict[str, Any]:
        """
        Strengthen a memory through verification or access
        
        Args:
            memory: The memory to strengthen
            verification_type: "access" | "confirm" | "verify"
            
        Returns:
            Updated memory with strengthened confidence
        """
        updated = memory.copy()
        
        # Update access tracking
        updated["access_count"] = memory.get("access_count", 0) + 1
        updated["last_accessed"] = datetime.utcnow().isoformat()
        
        # Update verification if explicitly confirmed
        if verification_type in ["confirm", "verify"]:
            updated["verification_count"] = memory.get("verification_count", 0) + 1
            
            # Upgrade source if verified
            current_source = memory.get("source", "unknown")
            if current_source not in ["user_explicit", "user_confirmed"]:
                updated["source"] = MemorySource.USER_CONFIRMED.value
        
        # Recalculate confidence
        updated["confidence"] = self.calculate_score(updated)
        updated["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(
            f"📈 Memory strengthened: confidence {memory.get('confidence', 0):.3f} → "
            f"{updated['confidence']:.3f}"
        )
        
        return updated
    
    def weaken(
        self,
        memory: Dict[str, Any],
        reason: str = "contradiction"
    ) -> Dict[str, Any]:
        """
        Weaken a memory's confidence
        
        Args:
            memory: The memory to weaken
            reason: Why it's being weakened
            
        Returns:
            Updated memory with weakened confidence
        """
        updated = memory.copy()
        
        # Reduce confidence
        current_confidence = memory.get("confidence", 0.5)
        reduction = 0.2 if reason == "contradiction" else 0.1
        updated["confidence"] = max(0.1, current_confidence - reduction)
        
        # Track weakness reason
        weakness_log = memory.get("weakness_log", [])
        weakness_log.append({
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "confidence_before": current_confidence,
            "confidence_after": updated["confidence"]
        })
        updated["weakness_log"] = weakness_log[-5:]  # Keep last 5
        
        updated["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(
            f"📉 Memory weakened ({reason}): confidence {current_confidence:.3f} → "
            f"{updated['confidence']:.3f}"
        )
        
        return updated
    
    def should_expire(self, memory: Dict[str, Any]) -> bool:
        """Check if a memory should be expired/deleted"""
        metadata = self._extract_metadata(memory)
        
        # Critical memories never expire
        if metadata.importance == MemoryImportance.CRITICAL:
            return False
        
        # Very low confidence = expire
        if metadata.confidence < 0.15:
            return True
        
        # Check age vs retention
        retention_days = self.IMPORTANCE_RETENTION.get(metadata.importance, 90)
        age_days = (datetime.utcnow() - metadata.created_at).days
        
        # Ephemeral memories expire quickly
        if metadata.importance == MemoryImportance.EPHEMERAL and age_days > 1:
            return True
        
        # Low importance with no recent access
        if metadata.importance == MemoryImportance.LOW:
            if age_days > retention_days and metadata.access_count < 3:
                return True
        
        return False
    
    def prioritize_memories(
        self,
        memories: List[Dict[str, Any]],
        context_query: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Prioritize memories by confidence and relevance
        
        Args:
            memories: List of memory items
            context_query: Current query for relevance matching
            top_k: Number of top memories to return
            
        Returns:
            Sorted list of memories (highest priority first)
        """
        scored_memories = []
        
        for memory in memories:
            score = self.calculate_score(memory)
            
            # Boost for query relevance (if provided)
            if context_query:
                relevance_boost = self._calculate_relevance(memory, context_query)
                score = score * 0.7 + relevance_boost * 0.3
            
            scored_memories.append((score, memory))
        
        # Sort by score (descending)
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        # Return top k with scores
        result = []
        for score, memory in scored_memories[:top_k]:
            memory_with_score = memory.copy()
            memory_with_score["_priority_score"] = score
            result.append(memory_with_score)
        
        return result
    
    def _calculate_relevance(self, memory: Dict[str, Any], query: str) -> float:
        """Calculate relevance of memory to query"""
        text = str(memory.get("text") or memory.get("value") or "").lower()
        query_lower = query.lower()
        
        # Simple word overlap scoring
        query_words = set(query_lower.split())
        text_words = set(text.split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words & text_words)
        relevance = overlap / len(query_words)
        
        return min(1.0, relevance)
    
    def enrich_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a memory with metadata and confidence score
        
        Call this before storing any new memory.
        """
        enriched = memory.copy()
        
        # 🆕 Map extraction confidence strings to source types
        # Check both "confidence" and "extraction_confidence" keys
        extraction_confidence = memory.get("confidence") or memory.get("extraction_confidence")
        if extraction_confidence in ["explicit", "strong"]:
            enriched["source"] = MemorySource.USER_EXPLICIT.value
        elif extraction_confidence in ["moderate"]:
            enriched["source"] = MemorySource.AI_EXTRACTED.value
        elif "source" not in enriched:
            enriched["source"] = MemorySource.UNKNOWN.value
        
        if "category" not in enriched:
            enriched["category"] = self.detect_category(memory).value
        
        if "importance" not in enriched:
            enriched["importance"] = self.detect_importance(memory).value
        
        # Add timestamps
        now = datetime.utcnow().isoformat()
        if "created_at" not in enriched:
            enriched["created_at"] = now
        enriched["updated_at"] = now
        enriched["last_accessed"] = now
        
        # Initialize counters
        if "access_count" not in enriched:
            enriched["access_count"] = 0
        if "verification_count" not in enriched:
            enriched["verification_count"] = 0
        if "version" not in enriched:
            enriched["version"] = 1
        
        # Calculate confidence
        enriched["confidence"] = self.calculate_score(enriched)
        
        return enriched


# Global singleton instance
memory_confidence = MemoryConfidence()
