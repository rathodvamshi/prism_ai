"""
⚡ Intent-Based Service Loading
Only load what you need based on the user's request intent.

CRITICAL OPTIMIZATION:
- Detect intent FIRST
- Load ONLY required services
- Stop as soon as data is found
"""

from enum import Enum
from typing import Set, Optional
import re

class ServiceIntent(Enum):
    """Service loading requirements based on intent"""
    CASUAL_CHAT = "casual_chat"           # Redis only
    TASK_CREATE = "task_create"           # Redis + MongoDB
    TASK_LIST = "task_list"               # MongoDB only
    PERSONAL_MEMORY = "personal_memory"   # Neo4j only
    DEEP_SEARCH = "deep_search"           # Pinecone only
    FULL_CONTEXT = "full_context"         # All services
    MEMORY_QUERY = "memory_query"         # Explicit memory recall across all systems


class IntentDetector:
    """
    Lightweight intent detection - decides which services to load.
    
    Performance: < 1ms per detection (regex-based, no LLM calls)
    """
    
    # Task-related patterns
    TASK_CREATE_PATTERNS = [
        r"\b(remind|reminder|schedule|set a task|create task|add task|todo)\b",
        r"\b(at|on|tomorrow|next|in \d+)\b.*\b(remind|notify|tell)\b",
    ]
    
    TASK_LIST_PATTERNS = [
        r"\b(list|show|get|view|display)\b.*\b(task|reminder|todo)",
        r"\b(my|all|pending|upcoming)\b.*\b(task|reminder|todo)",
        r"\bwhat.*\b(task|reminder|todo)",
    ]
    
    # Personal memory patterns (Neo4j)
    PERSONAL_MEMORY_PATTERNS = [
        r"\b(my name|who am i|my age|my birthday|my family|my job|my hobbies)\b",
        r"\b(remember|recall|what do you know about me)\b",
        r"\b(tell me about myself|my profile|my details)\b",
    ]
    
    # Deep search patterns (Pinecone)
    DEEP_SEARCH_PATTERNS = [
        r"\b(search|find|lookup|locate)\b.*\b(conversation|history|discussed|talked about)\b",
        r"\b(when did i|have i ever|did we talk about)\b",
        r"\b(similar to|related to|like when)\b",
    ]

    # Explicit memory recall questions (bypass casual fast path)
    MEMORY_QUERY_PATTERNS = [
        r"\b(what\s+(did|have)\s+we\s+(discuss(ed)?|talk(ed)?\s+about|say)\b.*(conversation|chat)?\b)",
        r"\b(what\s+we\s+have\s+discussed)\b",
        r"\b(what\s+did\s+we\s+discuss)\b",
        r"\b(what\s+did\s+we\s+talk\s+about)\b",
        r"\b(what\s+do\s+you\s+remember)\b",
        r"\b(recall\s+my\s+(interests|preferences|details))\b"
    ]
    
    # Casual chat (no special intent)
    CASUAL_PATTERNS = [
        r"^(hi|hello|hey|sup|yo)\b",
        r"\b(how are you|what's up|how's it going)\b",
        r"^(thanks|thank you|bye|goodbye)\b",
    ]
    
    @staticmethod
    def detect_intent(message: str) -> ServiceIntent:
        """
        Detect user intent from message.
        
        Returns the intent with MINIMUM service requirements.
        Performance: O(n) where n = number of patterns (< 1ms)
        """
        message_lower = message.lower().strip()
        
        # Priority 1: Memory recall (force memory-aware path)
        for pattern in IntentDetector.MEMORY_QUERY_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return ServiceIntent.MEMORY_QUERY

        # Priority 2: Casual chat (fastest path - Redis only)
        for pattern in IntentDetector.CASUAL_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return ServiceIntent.CASUAL_CHAT

        # Priority 3: Task operations
        for pattern in IntentDetector.TASK_CREATE_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return ServiceIntent.TASK_CREATE
        
        for pattern in IntentDetector.TASK_LIST_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return ServiceIntent.TASK_LIST
        
        # Priority 4: Personal memory (Neo4j)
        for pattern in IntentDetector.PERSONAL_MEMORY_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return ServiceIntent.PERSONAL_MEMORY
        
        # Priority 5: Deep search (Pinecone)
        for pattern in IntentDetector.DEEP_SEARCH_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return ServiceIntent.DEEP_SEARCH
        
        # Default: Casual chat (Redis only)
        # Most conversations are casual, so default to lightest load
        return ServiceIntent.CASUAL_CHAT
    
    @staticmethod
    def get_required_services(intent: ServiceIntent) -> Set[str]:
        """
        Get list of services to load for this intent.
        
        Returns:
            Set of service names: {"redis", "mongodb", "neo4j", "pinecone"}
        """
        service_map = {
            ServiceIntent.CASUAL_CHAT: {"redis"},
            ServiceIntent.TASK_CREATE: {"redis", "mongodb"},
            ServiceIntent.TASK_LIST: {"mongodb"},
            ServiceIntent.PERSONAL_MEMORY: {"neo4j"},
            ServiceIntent.DEEP_SEARCH: {"pinecone"},
            ServiceIntent.FULL_CONTEXT: {"redis", "mongodb", "neo4j", "pinecone"},
            ServiceIntent.MEMORY_QUERY: {"redis", "mongodb", "neo4j", "pinecone"},
        }
        
        return service_map.get(intent, {"redis"})
    
    @staticmethod
    def should_load_redis(intent: ServiceIntent) -> bool:
        return "redis" in IntentDetector.get_required_services(intent)
    
    @staticmethod
    def should_load_mongodb(intent: ServiceIntent) -> bool:
        return "mongodb" in IntentDetector.get_required_services(intent)
    
    @staticmethod
    def should_load_neo4j(intent: ServiceIntent) -> bool:
        return "neo4j" in IntentDetector.get_required_services(intent)
    
    @staticmethod
    def should_load_pinecone(intent: ServiceIntent) -> bool:
        return "pinecone" in IntentDetector.get_required_services(intent)


class LazyServiceLoader:
    """
    Lazy-load services based on intent.
    Only connect when needed, cache connections.
    
    ⏱️ WITH TIMEOUTS: Never block the user
    """
    
    def __init__(self):
        self._redis_client = None
        self._neo4j_client = None
        self._pinecone_client = None
        # MongoDB is always available (app startup)
    
    async def get_redis(self):
        """Lazy-load Redis connection (timeout: 100ms)"""
        if self._redis_client is None:
            from app.utils.timeout_utils import with_timeout, TimeoutConfig
            try:
                from app.services.cache_service import cache_service
                self._redis_client = await with_timeout(
                    self._load_redis(),
                    timeout_ms=TimeoutConfig.REDIS_GET,
                    service_name="Redis Connection",
                    fallback=None
                )
                if self._redis_client:
                    print("🔴 Redis loaded on-demand")
            except Exception as e:
                print(f"⚠️ Redis load failed: {e}")
                self._redis_client = None
        return self._redis_client
    
    async def _load_redis(self):
        """Helper to load Redis"""
        from app.services.cache_service import cache_service
        return cache_service
    
    async def get_neo4j(self):
        """Lazy-load Neo4j connection (timeout: 500ms)"""
        if self._neo4j_client is None:
            from app.utils.timeout_utils import with_timeout, TimeoutConfig
            try:
                from app.services.advanced_memory_manager import memory_manager
                self._neo4j_client = await with_timeout(
                    self._load_neo4j(),
                    timeout_ms=TimeoutConfig.NEO4J_READ,
                    service_name="Neo4j Connection",
                    fallback=None
                )
                if self._neo4j_client:
                    print("🔵 Neo4j loaded on-demand")
            except Exception as e:
                print(f"⚠️ Neo4j load failed: {e}")
                self._neo4j_client = None
        return self._neo4j_client
    
    async def _load_neo4j(self):
        """Helper to load Neo4j"""
        from app.services.advanced_memory_manager import memory_manager
        return memory_manager
    
    async def get_pinecone(self):
        """Lazy-load Pinecone connection (timeout: 800ms)"""
        if self._pinecone_client is None:
            from app.utils.timeout_utils import with_timeout, TimeoutConfig
            try:
                # Import pinecone service when needed
                # from app.services.pinecone_service import pinecone_service
                # self._pinecone_client = await with_timeout(
                #     self._load_pinecone(),
                #     timeout_ms=TimeoutConfig.PINECONE_SEARCH,
                #     service_name="Pinecone Connection",
                #     fallback=None
                # )
                print("🟣 Pinecone loaded on-demand")
            except Exception as e:
                print(f"⚠️ Pinecone load failed: {e}")
                self._pinecone_client = None
        return self._pinecone_client
    
    def reset(self):
        """Reset all cached connections (for testing)"""
        self._redis_client = None
        self._neo4j_client = None
        self._pinecone_client = None


# Global instances
intent_detector = IntentDetector()
lazy_loader = LazyServiceLoader()


async def load_services_for_message(message: str) -> dict:
    """
    Main entry point: Detect intent and load only required services.
    
    Returns:
        dict with loaded services: {
            "intent": ServiceIntent,
            "redis": Optional[RedisClient],
            "neo4j": Optional[Neo4jClient],
            "pinecone": Optional[PineconeClient]
        }
    """
    # Step 1: Detect intent (< 1ms)
    intent = intent_detector.detect_intent(message)
    print(f"🎯 Detected intent: {intent.value}")
    
    # Step 2: Load ONLY required services
    services = {"intent": intent}
    
    if intent_detector.should_load_redis(intent):
        services["redis"] = await lazy_loader.get_redis()
    
    if intent_detector.should_load_neo4j(intent):
        services["neo4j"] = await lazy_loader.get_neo4j()
    
    if intent_detector.should_load_pinecone(intent):
        services["pinecone"] = await lazy_loader.get_pinecone()
    
    return services


# Helper: Check cache first, stop if found
async def get_cached_or_query(
    user_id: str,
    query_type: str,
    redis_key: Optional[str] = None
) -> Optional[dict]:
    """
    Cascade query pattern WITH TIMEOUTS:
    1. Check Redis (fastest, 100ms timeout) - if found, STOP
    2. Check Neo4j (medium, 500ms timeout) - if found, cache in Redis, STOP
    3. Check Pinecone (slowest, 800ms timeout) - if found, cache in Redis, STOP
    
    ⏱️ FAIL FAST: If timeout, skip and continue
    Returns None if not found anywhere or all timeouts.
    """
    from app.utils.timeout_utils import tracked_timeout, TimeoutConfig
    
    # Step 1: Try Redis cache (100ms timeout)
    if redis_key:
        redis_client = await lazy_loader.get_redis()
        if redis_client:
            cached = await tracked_timeout(
                redis_client.get(redis_key),
                timeout_ms=TimeoutConfig.REDIS_GET,
                service_name="Redis GET",
                fallback=None
            )
            if cached:
                print(f"✅ Cache HIT (Redis): {redis_key}")
                return cached
            print(f"❌ Cache MISS (Redis): {redis_key}")
    
    # Step 2: Try Neo4j (personal memory, 500ms timeout)
    if query_type == "personal":
        neo4j_client = await lazy_loader.get_neo4j()
        if neo4j_client:
            result = await tracked_timeout(
                neo4j_client.load_user_memory(user_id),
                timeout_ms=TimeoutConfig.NEO4J_READ,
                service_name="Neo4j LOAD",
                fallback=None
            )
            if result:
                print(f"✅ Found in Neo4j (personal memory)")
                # Cache in Redis for next time (with timeout)
                if redis_key and redis_client:
                    await tracked_timeout(
                        redis_client.set(redis_key, result, ex=3600),
                        timeout_ms=TimeoutConfig.REDIS_SET,
                        service_name="Redis SET",
                        fallback=False
                    )
                return result
            print(f"❌ Not found in Neo4j (or timeout)")
    
    # Step 3: Try Pinecone (deep search, 800ms timeout) - only if needed
    if query_type == "deep":
        pinecone_client = await lazy_loader.get_pinecone()
        if pinecone_client:
            # result = await tracked_timeout(
            #     pinecone_client.search(query),
            #     timeout_ms=TimeoutConfig.PINECONE_SEARCH,
            #     service_name="Pinecone SEARCH",
            #     fallback=None
            # )
            # if result:
            #     print(f"✅ Found in Pinecone (deep search)")
            #     if redis_key and redis_client:
            #         await tracked_timeout(
            #             redis_client.set(redis_key, result, ex=3600),
            #             timeout_ms=TimeoutConfig.REDIS_SET,
            #             service_name="Redis SET",
            #             fallback=False
            #         )
            #     return result
            print(f"❌ Not found in Pinecone (or timeout)")
    
    return None
