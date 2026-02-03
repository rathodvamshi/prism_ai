"""
🔄 MEMORY DEDUPLICATION - Intelligent Duplicate Prevention
==========================================================

This module prevents duplicate memories and intelligently merges similar ones.

Key Features:
- Semantic similarity detection (not just exact match)
- Intelligent merge strategies for similar memories
- Contradiction detection and resolution
- Memory versioning for update tracking
- Consolidation of repetitive information

Usage:
    from app.services.memory_deduplication import MemoryDeduplicator, memory_deduplicator
    
    # Check before storing
    is_duplicate, existing = memory_deduplicator.check_duplicate(user_id, new_memory)
    
    # Merge if similar
    merged = memory_deduplicator.merge_memories(existing, new_memory)
"""

import logging
import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from difflib import SequenceMatcher
from collections import defaultdict

logger = logging.getLogger(__name__)


class DuplicateType:
    """Types of duplicate detection"""
    EXACT = "exact"              # Exact text match
    SEMANTIC = "semantic"        # Meaning is same but words differ
    PARTIAL = "partial"          # Overlapping information
    CONTRADICTION = "contradiction"  # Same topic but conflicting info
    UPDATE = "update"            # New version of existing info
    UNRELATED = "unrelated"      # No relationship


class MergeStrategy:
    """Strategies for merging memories"""
    KEEP_EXISTING = "keep_existing"      # Keep old, discard new
    REPLACE = "replace"                   # Replace old with new
    MERGE_APPEND = "merge_append"         # Combine information
    KEEP_BOTH = "keep_both"              # Store as separate versions
    UPDATE_CONFIDENCE = "update_confidence"  # Update metadata only


class MemoryDeduplicator:
    """
    🔄 MEMORY DEDUPLICATION SYSTEM
    
    Prevents duplicate memories and handles memory updates intelligently.
    Uses multiple strategies based on duplicate type.
    """
    
    def __init__(self):
        # Similarity thresholds
        self.EXACT_THRESHOLD = 0.98       # Above this = exact match
        self.SEMANTIC_THRESHOLD = 0.85    # Above this = semantic duplicate
        self.PARTIAL_THRESHOLD = 0.60     # Above this = partial overlap
        
        # Memory type specific thresholds (some types need stricter dedup)
        self.TYPE_THRESHOLDS = {
            "identity": 0.80,      # Stricter for names, etc.
            "location": 0.75,      # Stricter for places
            "preference": 0.70,    # More flexible for preferences
            "interest": 0.65,      # Even more flexible for interests
            "context": 0.90,       # Context needs high match
        }
        
        # Contradiction indicators
        self.CONTRADICTION_PATTERNS = [
            (r"\bnot\b", r"\bis\b"),
            (r"\bhate\b", r"\blove\b"),
            (r"\bdislike\b", r"\blike\b"),
            (r"\bnever\b", r"\balways\b"),
            (r"\bcan't\b", r"\bcan\b"),
            (r"\bwon't\b", r"\bwill\b"),
        ]
        
        # Cache for recent comparisons (avoid redundant computation)
        self._comparison_cache: Dict[str, Tuple[DuplicateType, float]] = {}
        self._cache_max_size = 1000
        
        logger.info("🔄 MemoryDeduplicator initialized")
    
    def check_duplicate(
        self,
        new_memory: Dict[str, Any],
        existing_memories: List[Dict[str, Any]],
        memory_type: Optional[str] = None
    ) -> Tuple[DuplicateType, Optional[Dict[str, Any]], float]:
        """
        Check if new memory is a duplicate of any existing memory
        
        Args:
            new_memory: The new memory to check
            existing_memories: List of existing memories to compare against
            memory_type: Type of memory for threshold selection
            
        Returns:
            Tuple of (duplicate_type, matching_memory_or_none, similarity_score)
        """
        new_text = self._extract_text(new_memory)
        if not new_text:
            return DuplicateType.UNRELATED, None, 0.0
        
        # Get threshold for this memory type
        threshold = self.TYPE_THRESHOLDS.get(memory_type, self.SEMANTIC_THRESHOLD)
        
        best_match = None
        best_score = 0.0
        best_type = DuplicateType.UNRELATED
        
        for existing in existing_memories:
            existing_text = self._extract_text(existing)
            if not existing_text:
                continue
            
            # Check cache first
            cache_key = self._get_cache_key(new_text, existing_text)
            if cache_key in self._comparison_cache:
                dup_type, score = self._comparison_cache[cache_key]
                if score > best_score:
                    best_score = score
                    best_type = dup_type
                    best_match = existing
                continue
            
            # Calculate similarity
            similarity = self._calculate_similarity(new_text, existing_text)
            
            # Determine duplicate type
            dup_type = self._classify_duplicate(
                new_text, existing_text, similarity, new_memory, existing
            )
            
            # Cache result
            self._cache_comparison(cache_key, dup_type, similarity)
            
            if similarity > best_score:
                best_score = similarity
                best_type = dup_type
                best_match = existing
        
        # Apply threshold
        if best_score < threshold and best_type not in [DuplicateType.CONTRADICTION, DuplicateType.UPDATE]:
            best_type = DuplicateType.UNRELATED
            best_match = None
        
        logger.debug(
            f"🔍 Duplicate check: type={best_type}, score={best_score:.3f}, "
            f"threshold={threshold}"
        )
        
        return best_type, best_match, best_score
    
    def _extract_text(self, memory: Dict[str, Any]) -> str:
        """Extract text content from memory"""
        text = memory.get("text") or memory.get("value") or memory.get("content", "")
        if isinstance(text, str):
            return text.strip().lower()
        return str(text).lower() if text else ""
    
    def _get_cache_key(self, text1: str, text2: str) -> str:
        """Generate cache key for comparison"""
        combined = f"{text1[:100]}||{text2[:100]}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _cache_comparison(self, key: str, dup_type: DuplicateType, score: float):
        """Cache comparison result"""
        if len(self._comparison_cache) >= self._cache_max_size:
            # Clear oldest half of cache
            keys = list(self._comparison_cache.keys())
            for k in keys[:len(keys)//2]:
                del self._comparison_cache[k]
        
        self._comparison_cache[key] = (dup_type, score)
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Public method for text similarity calculation"""
        return self._calculate_similarity(
            self._normalize_text(text1), 
            self._normalize_text(text2)
        )
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""
        # Lowercase, remove punctuation, normalize whitespace
        normalized = text.lower()
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts
        
        Uses multiple methods for robust comparison:
        1. Exact sequence matching
        2. Token overlap (Jaccard)
        3. Key entity overlap
        """
        if not text1 or not text2:
            return 0.0
        
        # 1. Sequence similarity (handles typos, word order)
        sequence_sim = SequenceMatcher(None, text1, text2).ratio()
        
        # 2. Token overlap (Jaccard similarity)
        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))
        
        if tokens1 and tokens2:
            intersection = len(tokens1 & tokens2)
            union = len(tokens1 | tokens2)
            jaccard_sim = intersection / union if union > 0 else 0
        else:
            jaccard_sim = 0
        
        # 3. Key entity overlap (proper nouns, numbers)
        entities1 = self._extract_entities(text1)
        entities2 = self._extract_entities(text2)
        
        if entities1 and entities2:
            entity_intersection = len(entities1 & entities2)
            entity_union = len(entities1 | entities2)
            entity_sim = entity_intersection / entity_union if entity_union > 0 else 0
        else:
            entity_sim = 0.5  # Neutral if no entities
        
        # Weighted combination
        combined = (
            sequence_sim * 0.4 +
            jaccard_sim * 0.35 +
            entity_sim * 0.25
        )
        
        return combined
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into meaningful words"""
        # Remove punctuation and split
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter stopwords
        stopwords = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "i", "me", "my", "you", "your", "he", "she", "it", "we", "they",
            "this", "that", "these", "those", "and", "or", "but", "in", "on",
            "at", "to", "for", "of", "with", "as", "by", "about", "into"
        }
        return [w for w in words if w not in stopwords and len(w) > 1]
    
    def _extract_entities(self, text: str) -> set:
        """Extract key entities (names, numbers, places)"""
        entities = set()
        
        # Proper nouns (capitalized words in original text)
        # Since we're working with lowercased text, use patterns
        
        # Numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        entities.update(numbers)
        
        # Known entity patterns
        patterns = [
            r'\b[a-z]+(?:ville|town|city|burg|land)\b',  # Places
            r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',  # Days
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',  # Months
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            entities.update(matches)
        
        return entities
    
    def _classify_duplicate(
        self,
        new_text: str,
        existing_text: str,
        similarity: float,
        new_memory: Dict[str, Any],
        existing_memory: Dict[str, Any]
    ) -> DuplicateType:
        """Classify the type of duplicate/relationship"""
        
        # Exact match
        if similarity >= self.EXACT_THRESHOLD:
            return DuplicateType.EXACT
        
        # Check for contradiction
        if self._is_contradiction(new_text, existing_text, new_memory, existing_memory):
            return DuplicateType.CONTRADICTION
        
        # Check if it's an update (same topic, newer info)
        if self._is_update(new_memory, existing_memory):
            return DuplicateType.UPDATE
        
        # Semantic duplicate
        if similarity >= self.SEMANTIC_THRESHOLD:
            return DuplicateType.SEMANTIC
        
        # Partial overlap
        if similarity >= self.PARTIAL_THRESHOLD:
            return DuplicateType.PARTIAL
        
        return DuplicateType.UNRELATED
    
    def _is_contradiction(
        self,
        new_text: str,
        existing_text: str,
        new_memory: Dict[str, Any],
        existing_memory: Dict[str, Any]
    ) -> bool:
        """Check if memories contradict each other"""
        
        # Same category but opposite sentiment
        new_cat = new_memory.get("category", "")
        existing_cat = existing_memory.get("category", "")
        
        if new_cat != existing_cat:
            return False  # Different categories can't contradict
        
        # Check contradiction patterns
        for neg_pattern, pos_pattern in self.CONTRADICTION_PATTERNS:
            new_has_neg = re.search(neg_pattern, new_text)
            existing_has_pos = re.search(pos_pattern, existing_text)
            new_has_pos = re.search(pos_pattern, new_text)
            existing_has_neg = re.search(neg_pattern, existing_text)
            
            # One has negative, other has positive on same topic
            if (new_has_neg and existing_has_pos) or (new_has_pos and existing_has_neg):
                # Check if they share key terms (same topic)
                new_tokens = set(self._tokenize(new_text))
                existing_tokens = set(self._tokenize(existing_text))
                overlap = new_tokens & existing_tokens
                
                if len(overlap) >= 2:  # Share at least 2 meaningful words
                    return True
        
        return False
    
    def _is_update(
        self,
        new_memory: Dict[str, Any],
        existing_memory: Dict[str, Any]
    ) -> bool:
        """Check if new memory is an update to existing"""
        
        # Same type/category
        new_type = new_memory.get("type") or new_memory.get("category", "")
        existing_type = existing_memory.get("type") or existing_memory.get("category", "")
        
        if new_type != existing_type:
            return False
        
        # Check timestamps
        new_time = new_memory.get("created_at") or new_memory.get("timestamp")
        existing_time = existing_memory.get("created_at") or existing_memory.get("timestamp")
        
        if new_time and existing_time:
            try:
                if isinstance(new_time, str):
                    new_time = datetime.fromisoformat(new_time.replace("Z", "+00:00"))
                if isinstance(existing_time, str):
                    existing_time = datetime.fromisoformat(existing_time.replace("Z", "+00:00"))
                
                # New is more recent
                if new_time > existing_time:
                    return True
            except:
                pass
        
        return False
    
    def get_merge_strategy(
        self,
        duplicate_type: DuplicateType,
        new_memory: Dict[str, Any],
        existing_memory: Dict[str, Any]
    ) -> MergeStrategy:
        """
        Determine the best merge strategy based on duplicate type
        """
        if duplicate_type == DuplicateType.EXACT:
            # Exact duplicate - just update confidence
            return MergeStrategy.UPDATE_CONFIDENCE
        
        if duplicate_type == DuplicateType.SEMANTIC:
            # Same meaning - keep higher confidence one
            new_conf = new_memory.get("confidence", 0.5)
            existing_conf = existing_memory.get("confidence", 0.5)
            
            if new_conf > existing_conf:
                return MergeStrategy.REPLACE
            else:
                return MergeStrategy.UPDATE_CONFIDENCE
        
        if duplicate_type == DuplicateType.PARTIAL:
            # Overlapping info - merge them
            return MergeStrategy.MERGE_APPEND
        
        if duplicate_type == DuplicateType.UPDATE:
            # Clear update - replace with new
            return MergeStrategy.REPLACE
        
        if duplicate_type == DuplicateType.CONTRADICTION:
            # Conflicting info - keep both for review
            return MergeStrategy.KEEP_BOTH
        
        # Default: keep existing
        return MergeStrategy.KEEP_EXISTING
    
    def merge_memories(
        self,
        existing_memory: Dict[str, Any],
        new_memory: Dict[str, Any],
        strategy: MergeStrategy
    ) -> Dict[str, Any]:
        """
        Merge two memories according to strategy
        
        Returns:
            Merged memory dict
        """
        if strategy == MergeStrategy.KEEP_EXISTING:
            result = existing_memory.copy()
            result["access_count"] = existing_memory.get("access_count", 0) + 1
            result["last_accessed"] = datetime.utcnow().isoformat()
            return result
        
        if strategy == MergeStrategy.REPLACE:
            result = new_memory.copy()
            # Preserve some existing metadata
            result["version"] = existing_memory.get("version", 1) + 1
            result["previous_version"] = existing_memory.get("text") or existing_memory.get("value")
            result["replaced_at"] = datetime.utcnow().isoformat()
            return result
        
        if strategy == MergeStrategy.UPDATE_CONFIDENCE:
            result = existing_memory.copy()
            # Boost confidence (memory confirmed)
            existing_conf = existing_memory.get("confidence", 0.5)
            result["confidence"] = min(1.0, existing_conf + 0.1)
            result["verification_count"] = existing_memory.get("verification_count", 0) + 1
            result["last_verified"] = datetime.utcnow().isoformat()
            return result
        
        if strategy == MergeStrategy.MERGE_APPEND:
            result = existing_memory.copy()
            
            # Merge text content
            existing_text = self._extract_text(existing_memory)
            new_text = self._extract_text(new_memory)
            
            # Only append truly new information
            new_tokens = set(self._tokenize(new_text))
            existing_tokens = set(self._tokenize(existing_text))
            unique_new = new_tokens - existing_tokens
            
            if unique_new:
                # Append new unique info
                merged_text = f"{existing_text}. Additional: {' '.join(unique_new)}"
                if "text" in result:
                    result["text"] = merged_text
                elif "value" in result:
                    result["value"] = merged_text
            
            result["version"] = existing_memory.get("version", 1) + 1
            result["merged_at"] = datetime.utcnow().isoformat()
            return result
        
        if strategy == MergeStrategy.KEEP_BOTH:
            # Return existing with flag to also store new
            result = existing_memory.copy()
            result["_also_store_new"] = True
            result["_new_memory"] = new_memory
            result["_conflict_detected"] = True
            result["conflict_detected_at"] = datetime.utcnow().isoformat()
            return result
        
        # Default: return existing
        return existing_memory.copy()
    
    def consolidate_memories(
        self,
        memories: List[Dict[str, Any]],
        similarity_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """
        Consolidate a list of memories by merging similar ones
        
        Use this for batch cleanup/optimization.
        
        Args:
            memories: List of memories to consolidate
            similarity_threshold: Threshold for merging
            
        Returns:
            Consolidated list of memories
        """
        if not memories:
            return []
        
        if len(memories) == 1:
            return memories
        
        # Group by category first
        by_category = defaultdict(list)
        for mem in memories:
            cat = mem.get("category") or mem.get("type") or "general"
            by_category[cat].append(mem)
        
        consolidated = []
        
        for category, cat_memories in by_category.items():
            # Sort by confidence (highest first)
            cat_memories.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
            
            merged_indices = set()
            
            for i, mem1 in enumerate(cat_memories):
                if i in merged_indices:
                    continue
                
                current = mem1.copy()
                
                for j, mem2 in enumerate(cat_memories[i+1:], i+1):
                    if j in merged_indices:
                        continue
                    
                    text1 = self._extract_text(current)
                    text2 = self._extract_text(mem2)
                    similarity = self._calculate_similarity(text1, text2)
                    
                    if similarity >= similarity_threshold:
                        # Merge into current
                        strategy = self.get_merge_strategy(
                            DuplicateType.SEMANTIC, mem2, current
                        )
                        current = self.merge_memories(current, mem2, strategy)
                        merged_indices.add(j)
                
                consolidated.append(current)
        
        logger.info(
            f"🔄 Consolidated {len(memories)} memories into {len(consolidated)}"
        )
        
        return consolidated
    
    def find_contradictions(
        self,
        memories: List[Dict[str, Any]]
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any], str]]:
        """
        Find contradicting memories in a list
        
        Returns:
            List of (memory1, memory2, reason) tuples
        """
        contradictions = []
        
        for i, mem1 in enumerate(memories):
            for mem2 in memories[i+1:]:
                text1 = self._extract_text(mem1)
                text2 = self._extract_text(mem2)
                
                if self._is_contradiction(text1, text2, mem1, mem2):
                    reason = self._get_contradiction_reason(text1, text2)
                    contradictions.append((mem1, mem2, reason))
        
        return contradictions
    
    def detect_contradiction(
        self,
        memory1: Dict[str, Any],
        memory2: Dict[str, Any]
    ) -> bool:
        """
        Public method to check if two memories contradict each other
        
        Args:
            memory1: First memory
            memory2: Second memory
            
        Returns:
            True if memories contradict each other
        """
        text1 = self._extract_text(memory1)
        text2 = self._extract_text(memory2)
        return self._is_contradiction(text1, text2, memory1, memory2)
        
        return contradictions
    
    def _get_contradiction_reason(self, text1: str, text2: str) -> str:
        """Get human-readable reason for contradiction"""
        for neg_pattern, pos_pattern in self.CONTRADICTION_PATTERNS:
            if re.search(neg_pattern, text1) and re.search(pos_pattern, text2):
                neg_word = re.search(neg_pattern, text1).group()
                pos_word = re.search(pos_pattern, text2).group()
                return f"Conflicting statements: '{neg_word}' vs '{pos_word}'"
            
            if re.search(pos_pattern, text1) and re.search(neg_pattern, text2):
                pos_word = re.search(pos_pattern, text1).group()
                neg_word = re.search(neg_pattern, text2).group()
                return f"Conflicting statements: '{pos_word}' vs '{neg_word}'"
        
        return "Semantic contradiction detected"
    
    def generate_memory_hash(self, memory: Dict[str, Any]) -> str:
        """
        Generate a deterministic hash for a memory
        
        Useful for quick duplicate checking.
        """
        text = self._extract_text(memory)
        mem_type = memory.get("type") or memory.get("category", "general")
        user_id = memory.get("user_id", "")
        
        content = f"{user_id}|{mem_type}|{text}"
        return hashlib.sha256(content.encode()).hexdigest()


# Global singleton instance
memory_deduplicator = MemoryDeduplicator()
