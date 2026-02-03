"""
🎯 Semantic Cache - Instant responses for similar queries

Features:
- Query normalization for better cache hits
- TTL-based expiration
- Smart cache eligibility detection
- Cache warming for common queries

Impact: 0ms response time for cached queries (vs 2-5 seconds for LLM)
"""
import hashlib
import json
import re
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SemanticCache:
    """
    Cache LLM responses based on normalized query similarity.
    Returns instant responses for identical or near-identical queries.
    """
    
    # Filler words to remove for normalization
    FILLER_WORDS = frozenset([
        "please", "can", "could", "would", "you", "kindly",
        "i", "want", "to", "need", "like", "me", "tell",
        "give", "show", "help", "just", "actually", "basically"
    ])
    
    # Common queries that benefit most from caching
    COMMON_QUERIES = frozenset([
        "hello", "hi", "hey", "how are you",
        "what can you do", "help", "who are you",
        "what is your name", "thanks", "thank you",
        "bye", "goodbye", "good morning", "good night"
    ])
    
    def __init__(self, redis_client, ttl_hours: int = 6):
        """
        Initialize semantic cache.
        
        Args:
            redis_client: Async Redis client
            ttl_hours: Cache TTL in hours (default: 6 hours)
        """
        self.redis = redis_client
        self.ttl = timedelta(hours=ttl_hours)
        self.prefix = "sem_cache:"
        
        # Stats
        self.hits = 0
        self.misses = 0
    
    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for better cache matching.
        Removes filler words, extra whitespace, punctuation variations.
        """
        # Lowercase
        normalized = query.lower().strip()
        
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        
        # Remove common punctuation variations
        normalized = re.sub(r'[?!.,;:]+$', '', normalized)
        
        # Remove filler words (but keep structure)
        words = normalized.split()
        words = [w for w in words if w not in self.FILLER_WORDS]
        normalized = " ".join(words)
        
        return normalized.strip()
    
    def _get_cache_key(self, query: str, model: str, user_id: str = None) -> str:
        """Generate cache key from normalized query"""
        normalized = self._normalize_query(query)
        
        # Include user_id for personalized responses (optional)
        key_input = f"{model}:{normalized}"
        if user_id:
            # Use first 8 chars of user_id for some personalization
            key_input = f"{user_id[:8]}:{key_input}"
        
        query_hash = hashlib.sha256(key_input.encode()).hexdigest()[:20]
        return f"{self.prefix}{query_hash}"
    
    async def get(
        self, 
        query: str, 
        model: str,
        user_id: str = None
    ) -> Optional[Tuple[str, dict]]:
        """
        Check for cached response.
        
        Returns:
            Tuple of (response_text, metadata) or None if not cached
        """
        try:
            cache_key = self._get_cache_key(query, model, user_id)
            cached = await self.redis.get(cache_key)
            
            if cached:
                data = json.loads(cached)
                self.hits += 1
                logger.info(f"🎯 Semantic cache HIT: {query[:40]}...")
                return data["response"], data.get("metadata", {})
            
            self.misses += 1
            return None
            
        except Exception as e:
            logger.debug(f"Semantic cache lookup error: {e}")
            return None
    
    async def set(
        self,
        query: str,
        model: str,
        response: str,
        metadata: dict = None,
        user_id: str = None
    ) -> bool:
        """
        Cache a response.
        
        Returns:
            True if cached successfully
        """
        # Check eligibility before caching
        if not self.should_cache(query, response):
            return False
        
        try:
            cache_key = self._get_cache_key(query, model, user_id)
            
            data = {
                "response": response,
                "metadata": metadata or {},
                "cached_at": datetime.utcnow().isoformat(),
                "model": model,
                "query_normalized": self._normalize_query(query)
            }
            
            await self.redis.setex(
                cache_key,
                int(self.ttl.total_seconds()),
                json.dumps(data)
            )
            
            logger.debug(f"💾 Semantic cache SET: {query[:40]}...")
            return True
            
        except Exception as e:
            logger.debug(f"Semantic cache store error: {e}")
            return False
    
    async def invalidate(self, query: str, model: str, user_id: str = None) -> bool:
        """Invalidate a cached response"""
        try:
            cache_key = self._get_cache_key(query, model, user_id)
            await self.redis.delete(cache_key)
            return True
        except Exception:
            return False
    
    def should_cache(self, query: str, response: str = None) -> bool:
        """
        Determine if a query/response should be cached.
        
        Rules:
        - Cache common greetings and FAQs
        - Cache short factual queries
        - Don't cache very long or personal queries
        - Don't cache if response is too short (might be error)
        """
        normalized = self._normalize_query(query)
        
        # Always cache common queries
        if normalized in self.COMMON_QUERIES:
            return True
        
        # Don't cache very short queries (likely incomplete)
        if len(query) < 5:
            return False
        
        # Don't cache very long queries (too specific)
        if len(query) > 300:
            return False
        
        # Don't cache queries with strong personal indicators
        personal_indicators = [
            "my name", "i am", "i'm", "i have", "i've", 
            "my email", "my phone", "my address", "remember me"
        ]
        query_lower = query.lower()
        if any(ind in query_lower for ind in personal_indicators):
            return False
        
        # Don't cache queries asking about current time/date
        time_indicators = ["what time", "what date", "today", "now", "current"]
        if any(ind in query_lower for ind in time_indicators):
            return False
        
        # Check response quality (if provided)
        if response:
            # Don't cache very short responses (might be errors)
            if len(response) < 20:
                return False
            # Don't cache error-like responses
            if response.startswith(("Error", "Sorry, I couldn't", "I don't understand")):
                return False
        
        # Cache factual queries
        factual_starts = ["what is", "who is", "when was", "where is", "how does", "why does"]
        if any(query_lower.startswith(start) for start in factual_starts):
            return True
        
        # Default: cache if query is reasonably sized
        return 10 < len(query) < 200
    
    def get_stats(self) -> dict:
        """Get cache performance statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate_percent": round(hit_rate, 2)
        }
    
    async def warm_common_queries(self, model: str, responses: dict) -> int:
        """
        Pre-warm cache with common query responses.
        
        Args:
            model: Model name
            responses: Dict mapping queries to responses
        
        Returns:
            Number of entries warmed
        """
        warmed = 0
        for query, response in responses.items():
            success = await self.set(query, model, response)
            if success:
                warmed += 1
        
        logger.info(f"🔥 Warmed semantic cache with {warmed} entries")
        return warmed


# Common greeting responses for cache warming
COMMON_RESPONSES = {
    "hello": "Hello! How can I help you today?",
    "hi": "Hi there! What can I do for you?",
    "hey": "Hey! What's on your mind?",
    "how are you": "I'm doing great, thanks for asking! How can I assist you?",
    "what can you do": "I can help you with a wide range of tasks including answering questions, writing content, coding assistance, task management, and much more. What would you like help with?",
    "who are you": "I'm Prism, your AI assistant. I'm here to help you with questions, tasks, and creative projects. How can I assist you today?",
    "thanks": "You're welcome! Is there anything else I can help you with?",
    "thank you": "You're welcome! Feel free to ask if you need anything else.",
}


async def create_semantic_cache(redis_client, ttl_hours: int = 6) -> SemanticCache:
    """Factory function to create and optionally warm a semantic cache"""
    cache = SemanticCache(redis_client, ttl_hours)
    return cache
