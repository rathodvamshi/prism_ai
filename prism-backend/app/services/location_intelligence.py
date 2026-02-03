"""
🌍 Location Intelligence Service

Smart location resolution system that automatically infers location from:
1. User profile (MongoDB)
2. Session context  
3. Conversation memory
4. IP-based fallback (optional)

Only asks user for location as a last resort.
"""

from typing import Optional, Dict, Any, Tuple
import logging
import re
from datetime import datetime
from app.db.mongo_client import users_collection
from app.db.redis_client import redis_client
from bson import ObjectId
import json

logger = logging.getLogger(__name__)


class LocationIntelligence:
    """
    Smart location resolution with confidence scoring.
    
    Priority Order:
    1. User Profile (MongoDB) - highest confidence
    2. Session Context (Redis) - high confidence  
    3. Conversation Memory - medium confidence
    4. IP Fallback - low confidence
    5. Ask User - last resort
    """
    
    def __init__(self):
        self.location_cache = {}  # In-memory cache for session
        
    async def resolve_location(
        self, 
        user_id: str, 
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Intelligently resolve user location with confidence scoring.
        
        Returns:
            {
                "location": "Hyderabad, Telangana, India",
                "city": "Hyderabad",
                "state": "Telangana", 
                "country": "India",
                "confidence": 0.95,  # 0-1 scale
                "source": "user_profile",  # user_profile|session|memory|ip|none
                "should_confirm": False,  # Whether to confirm with user
                "display_text": "near you in Hyderabad"  # Human-friendly text
            }
        """
        logger.info(f"🌍 [Location] Resolving location for user {user_id}")
        
        # Step 1: Check cache (fastest)
        cache_key = f"location:{user_id}"
        if user_id in self.location_cache:
            logger.info(f"✅ [Location] Cache hit for user {user_id}")
            return self.location_cache[user_id]
        
        # Step 2: User Profile (MongoDB) - Most reliable
        profile_location = await self._get_profile_location(user_id)
        if profile_location and profile_location.get("confidence", 0) >= 0.8:
            self.location_cache[user_id] = profile_location
            await self._cache_to_redis(user_id, profile_location)
            return profile_location
        
        # Step 3: Session Context (Redis)
        session_location = await self._get_session_location(user_id, session_id)
        if session_location and session_location.get("confidence", 0) >= 0.7:
            self.location_cache[user_id] = session_location
            return session_location
        
        # Step 4: Extract from query (e.g., "temples near me")
        query_location = await self._extract_from_query(user_id, query)
        if query_location and query_location.get("confidence", 0) >= 0.6:
            # Store for future use
            await self._update_session_location(user_id, query_location)
            self.location_cache[user_id] = query_location
            return query_location
        
        # Step 5: No reliable location found
        logger.warning(f"⚠️ [Location] No reliable location for user {user_id}")
        return {
            "location": None,
            "city": None,
            "state": None,
            "country": None,
            "confidence": 0.0,
            "source": "none",
            "should_confirm": False,
            "should_ask": True,  # Flag to ask user
            "display_text": None
        }
    
    async def _get_profile_location(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get location from user profile (MongoDB)"""
        try:
            user = await users_collection.find_one(
                {"_id": ObjectId(user_id)},
                {"profile.location": 1, "profile.city": 1, "profile.state": 1, "profile.country": 1, "_id": 0}
            )
            
            if not user:
                return None
            
            profile = user.get("profile", {})
            location = profile.get("location")
            city = profile.get("city")
            state = profile.get("state")
            country = profile.get("country")
            
            # Build complete location string
            location_parts = []
            if city:
                location_parts.append(city)
            if state:
                location_parts.append(state)
            if country:
                location_parts.append(country)
            
            if not location_parts and not location:
                return None
            
            full_location = location or ", ".join(location_parts)
            
            logger.info(f"✅ [Location] Found in profile: {full_location}")
            
            return {
                "location": full_location,
                "city": city,
                "state": state,
                "country": country,
                "confidence": 0.95,  # Highest confidence - direct from profile
                "source": "user_profile",
                "should_confirm": False,
                "should_ask": False,
                "display_text": f"near you in {city or full_location}"
            }
            
        except Exception as e:
            logger.error(f"❌ [Location] Error getting profile location: {e}")
            return None
    
    async def _get_session_location(
        self, 
        user_id: str, 
        session_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Get location from session context (Redis)"""
        try:
            # Try session-specific location
            if session_id:
                session_key = f"session:location:{session_id}"
                location_data = await redis_client.get(session_key)
                if location_data:
                    data = json.loads(location_data)
                    data["source"] = "session"
                    logger.info(f"✅ [Location] Found in session: {data.get('location')}")
                    return data
            
            # Fallback to user-level location
            user_key = f"user:location:{user_id}"
            location_data = await redis_client.get(user_key)
            if location_data:
                data = json.loads(location_data)
                data["source"] = "session"
                logger.info(f"✅ [Location] Found in user cache: {data.get('location')}")
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ [Location] Error getting session location: {e}")
            return None
    
    async def _extract_from_query(self, user_id: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Extract location from query patterns:
        - "near me" / "around here" / "close by" → use last known location
        - "in [city]" → extract explicit city
        - "temples in Hyderabad" → extract Hyderabad
        """
        try:
            query_lower = query.lower().strip()
            
            # Pattern 1: "near me" variations (use profile location)
            near_me_patterns = [
                r"\bnear\s+me\b",
                r"\baround\s+(here|me)\b",
                r"\bclose\s+by\b",
                r"\bnearby\b",
                r"\bin\s+my\s+area\b",
                r"\bmy\s+location\b"
            ]
            
            for pattern in near_me_patterns:
                if re.search(pattern, query_lower):
                    # Use profile location
                    profile_location = await self._get_profile_location(user_id)
                    if profile_location:
                        logger.info(f"✅ [Location] 'near me' detected, using profile location")
                        return profile_location
            
            # Pattern 2: Explicit city mention "in [city]"
            city_pattern = r"\bin\s+([A-Z][a-zA-Z\s]+?)(?:\s+for|\s+\?|$)"
            match = re.search(city_pattern, query)
            if match:
                city = match.group(1).strip()
                logger.info(f"✅ [Location] Extracted city from query: {city}")
                return {
                    "location": city,
                    "city": city,
                    "state": None,
                    "country": None,
                    "confidence": 0.75,
                    "source": "query",
                    "should_confirm": True,  # Confirm since extracted from query
                    "should_ask": False,
                    "display_text": f"in {city}"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ [Location] Error extracting from query: {e}")
            return None
    
    async def _cache_to_redis(self, user_id: str, location_data: Dict[str, Any]):
        """Cache location to Redis for fast access"""
        try:
            cache_key = f"user:location:{user_id}"
            await redis_client.set(
                cache_key, 
                json.dumps(location_data), 
                ex=3600  # 1 hour TTL
            )
            logger.info(f"✅ [Location] Cached to Redis for user {user_id}")
        except Exception as e:
            logger.error(f"❌ [Location] Error caching to Redis: {e}")
    
    async def _update_session_location(self, user_id: str, location_data: Dict[str, Any]):
        """Update session location in Redis"""
        try:
            user_key = f"user:location:{user_id}"
            await redis_client.set(
                user_key,
                json.dumps(location_data),
                ex=7200  # 2 hours TTL
            )
            logger.info(f"✅ [Location] Updated session location for user {user_id}")
        except Exception as e:
            logger.error(f"❌ [Location] Error updating session location: {e}")
    
    async def update_user_location(
        self,
        user_id: str,
        location: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None
    ) -> bool:
        """
        Update user location in profile and memory.
        Called when user provides location explicitly.
        """
        try:
            # Update MongoDB profile
            update_data = {"profile.location": location}
            if city:
                update_data["profile.city"] = city
            if state:
                update_data["profile.state"] = state
            if country:
                update_data["profile.country"] = country
            
            result = await users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ [Location] Updated profile for user {user_id}: {location}")
                
                # Update cache
                location_data = {
                    "location": location,
                    "city": city,
                    "state": state,
                    "country": country,
                    "confidence": 0.95,
                    "source": "user_profile",
                    "should_confirm": False,
                    "should_ask": False,
                    "display_text": f"near you in {city or location}"
                }
                
                self.location_cache[user_id] = location_data
                await self._cache_to_redis(user_id, location_data)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ [Location] Error updating user location: {e}")
            return False
    
    def detect_location_query(self, query: str) -> bool:
        """
        Detect if query requires location context.
        
        Patterns:
        - "near me" / "around here"
        - "temples near me"
        - "restaurants nearby"
        - "find X close by"
        """
        query_lower = query.lower().strip()
        
        location_indicators = [
            r"\bnear\s+(me|here)\b",
            r"\baround\s+(here|me)\b",
            r"\bclose\s+by\b",
            r"\bnearby\b",
            r"\bin\s+my\s+area\b",
            r"\bmy\s+location\b",
            r"\bfind\s+.+\s+near\b",
            r"\bsearch\s+.+\s+around\b",
            r"\blocal\s+",
            r"\bin\s+the\s+vicinity\b"
        ]
        
        for pattern in location_indicators:
            if re.search(pattern, query_lower):
                return True
        
        return False
    
    async def get_location_context_string(
        self,
        user_id: str,
        query: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Get formatted location context string for LLM prompt.
        
        Returns human-friendly location context like:
        - "User is in Hyderabad, Telangana, India"
        - "User location: Bangalore (from session context)"
        - "Location: Unknown (please ask user if needed)"
        """
        location_data = await self.resolve_location(user_id, query, session_id)
        
        if location_data.get("location"):
            location = location_data["location"]
            source = location_data["source"]
            confidence = location_data["confidence"]
            
            context = f"User Location: {location}"
            
            if confidence >= 0.9:
                context += " (verified from profile)"
            elif confidence >= 0.7:
                context += " (from recent session)"
            else:
                context += " (low confidence, confirm if critical)"
            
            return context
        else:
            return "User Location: Unknown (ask user if location is required for the query)"


# Global instance
location_intelligence = LocationIntelligence()


# Convenience functions
async def get_user_location(
    user_id: str,
    query: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get user location with smart resolution"""
    return await location_intelligence.resolve_location(user_id, query, session_id)


async def get_location_context(
    user_id: str,
    query: str,
    session_id: Optional[str] = None
) -> str:
    """Get location context string for LLM"""
    return await location_intelligence.get_location_context_string(user_id, query, session_id)


def is_location_query(query: str) -> bool:
    """Check if query needs location"""
    return location_intelligence.detect_location_query(query)


async def update_location(
    user_id: str,
    location: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None
) -> bool:
    """Update user location"""
    return await location_intelligence.update_user_location(
        user_id, location, city, state, country
    )
