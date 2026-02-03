"""
🧠 Pre-Response Intelligence Check

Prevents the model from asking redundant questions by checking
available context and data BEFORE generating response.

Key Checks:
1. Do we already have this information?
2. Can we infer it with high confidence?
3. Have we asked this before in this session?
"""

from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime
from app.db.mongo_client import users_collection
from app.db.redis_client import redis_client
from bson import ObjectId
import json
import re

logger = logging.getLogger(__name__)


class PreResponseIntelligence:
    """
    Smart check system that prevents redundant questions.
    
    Evaluates:
    - User profile data (MongoDB)
    - Session context (Redis)
    - Conversation history
    """
    
    def __init__(self):
        self.question_history = {}  # Track questions asked per session
    
    async def check_before_asking(
        self,
        user_id: str,
        question: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check if we should ask this question or if we already have the answer.
        
        Returns:
            {
                "should_ask": False,  # Should we ask the user?
                "have_answer": True,  # Do we already have the answer?
                "answer": "Hyderabad",  # The answer we have
                "confidence": 0.95,  # Confidence in the answer
                "source": "user_profile",  # Where we got it from
                "reasoning": "Found in user profile"  # Explanation
            }
        """
        logger.info(f"🧠 [Intelligence] Checking question: {question}")
        
        # Parse question to understand what's being asked
        question_type = self._classify_question(question)
        
        if question_type == "location":
            return await self._check_location_availability(user_id, question, context)
        elif question_type == "name":
            return await self._check_name_availability(user_id, question, context)
        elif question_type == "preferences":
            return await self._check_preferences_availability(user_id, question, context)
        elif question_type == "time":
            return await self._check_time_availability(user_id, question, context)
        else:
            # Unknown question type - allow asking
            return {
                "should_ask": True,
                "have_answer": False,
                "answer": None,
                "confidence": 0.0,
                "source": None,
                "reasoning": "Question type not recognized"
            }
    
    def _classify_question(self, question: str) -> str:
        """Classify what type of information is being asked"""
        question_lower = question.lower().strip()
        
        # Location questions
        location_patterns = [
            r"(where|which|what)\s+(location|city|place|area)",
            r"(where\s+(are|is)\s+you|where\s+do\s+you\s+live)",
            r"your\s+location",
            r"which\s+city"
        ]
        for pattern in location_patterns:
            if re.search(pattern, question_lower):
                return "location"
        
        # Name questions
        name_patterns = [
            r"(what|whats)\s+(is\s+)?(your|ur)\s+name",
            r"(what|whats)\s+should\s+i\s+call\s+you",
            r"(may|can)\s+i\s+(have|know|get)\s+your\s+name"
        ]
        for pattern in name_patterns:
            if re.search(pattern, question_lower):
                return "name"
        
        # Preference questions
        pref_patterns = [
            r"what\s+do\s+you\s+(like|prefer|enjoy)",
            r"do\s+you\s+(like|prefer|want)",
            r"(your|ur)\s+(favorite|favourite|preferred)"
        ]
        for pattern in pref_patterns:
            if re.search(pattern, question_lower):
                return "preferences"
        
        # Time questions
        time_patterns = [
            r"what\s+time",
            r"when\s+(should|would|do\s+you\s+want)",
            r"(your|ur)\s+preferred\s+time"
        ]
        for pattern in time_patterns:
            if re.search(pattern, question_lower):
                return "time"
        
        return "unknown"
    
    async def _check_location_availability(
        self,
        user_id: str,
        question: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check if we have location information"""
        try:
            # Check user profile
            user = await users_collection.find_one(
                {"_id": ObjectId(user_id)},
                {"profile.location": 1, "profile.city": 1, "_id": 0}
            )
            
            if user:
                profile = user.get("profile", {})
                location = profile.get("location") or profile.get("city")
                
                if location:
                    logger.info(f"✅ [Intelligence] Have location: {location}")
                    return {
                        "should_ask": False,
                        "have_answer": True,
                        "answer": location,
                        "confidence": 0.95,
                        "source": "user_profile",
                        "reasoning": f"Found location in user profile: {location}"
                    }
            
            # Check context if provided
            if context and "location" in context:
                location = context["location"]
                logger.info(f"✅ [Intelligence] Have location from context: {location}")
                return {
                    "should_ask": False,
                    "have_answer": True,
                    "answer": location,
                    "confidence": 0.85,
                    "source": "context",
                    "reasoning": f"Found location in context: {location}"
                }
            
            # No location found
            logger.info(f"❌ [Intelligence] No location available")
            return {
                "should_ask": True,
                "have_answer": False,
                "answer": None,
                "confidence": 0.0,
                "source": None,
                "reasoning": "No location found in profile or context"
            }
            
        except Exception as e:
            logger.error(f"❌ [Intelligence] Error checking location: {e}")
            return {
                "should_ask": True,
                "have_answer": False,
                "answer": None,
                "confidence": 0.0,
                "source": None,
                "reasoning": f"Error: {str(e)}"
            }
    
    async def _check_name_availability(
        self,
        user_id: str,
        question: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check if we have user name"""
        try:
            user = await users_collection.find_one(
                {"_id": ObjectId(user_id)},
                {"name": 1, "profile.name": 1, "_id": 0}
            )
            
            if user:
                name = user.get("name") or user.get("profile", {}).get("name")
                
                if name:
                    logger.info(f"✅ [Intelligence] Have name: {name}")
                    return {
                        "should_ask": False,
                        "have_answer": True,
                        "answer": name,
                        "confidence": 1.0,
                        "source": "user_profile",
                        "reasoning": f"Found name in user profile: {name}"
                    }
            
            return {
                "should_ask": True,
                "have_answer": False,
                "answer": None,
                "confidence": 0.0,
                "source": None,
                "reasoning": "No name found in profile"
            }
            
        except Exception as e:
            logger.error(f"❌ [Intelligence] Error checking name: {e}")
            return {
                "should_ask": True,
                "have_answer": False,
                "answer": None,
                "confidence": 0.0,
                "source": None,
                "reasoning": f"Error: {str(e)}"
            }
    
    async def _check_preferences_availability(
        self,
        user_id: str,
        question: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check if we have user preferences"""
        try:
            user = await users_collection.find_one(
                {"_id": ObjectId(user_id)},
                {"interests": 1, "hobbies": 1, "profile.preferences": 1, "_id": 0}
            )
            
            if user:
                interests = user.get("interests", [])
                hobbies = user.get("hobbies", [])
                preferences = user.get("profile", {}).get("preferences", {})
                
                if interests or hobbies or preferences:
                    pref_summary = {
                        "interests": interests,
                        "hobbies": hobbies,
                        "preferences": preferences
                    }
                    logger.info(f"✅ [Intelligence] Have preferences: {pref_summary}")
                    return {
                        "should_ask": False,
                        "have_answer": True,
                        "answer": pref_summary,
                        "confidence": 0.90,
                        "source": "user_profile",
                        "reasoning": f"Found preferences in user profile"
                    }
            
            return {
                "should_ask": True,
                "have_answer": False,
                "answer": None,
                "confidence": 0.0,
                "source": None,
                "reasoning": "No preferences found in profile"
            }
            
        except Exception as e:
            logger.error(f"❌ [Intelligence] Error checking preferences: {e}")
            return {
                "should_ask": True,
                "have_answer": False,
                "answer": None,
                "confidence": 0.0,
                "source": None,
                "reasoning": f"Error: {str(e)}"
            }
    
    async def _check_time_availability(
        self,
        user_id: str,
        question: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check if we have time/timezone information"""
        try:
            user = await users_collection.find_one(
                {"_id": ObjectId(user_id)},
                {"profile.timezone": 1, "_id": 0}
            )
            
            if user:
                timezone = user.get("profile", {}).get("timezone")
                
                if timezone:
                    logger.info(f"✅ [Intelligence] Have timezone: {timezone}")
                    return {
                        "should_ask": False,
                        "have_answer": True,
                        "answer": timezone,
                        "confidence": 0.90,
                        "source": "user_profile",
                        "reasoning": f"Found timezone in user profile: {timezone}"
                    }
            
            return {
                "should_ask": True,
                "have_answer": False,
                "answer": None,
                "confidence": 0.0,
                "source": None,
                "reasoning": "No timezone found in profile"
            }
            
        except Exception as e:
            logger.error(f"❌ [Intelligence] Error checking time: {e}")
            return {
                "should_ask": True,
                "have_answer": False,
                "answer": None,
                "confidence": 0.0,
                "source": None,
                "reasoning": f"Error: {str(e)}"
            }
    
    async def detect_redundant_question_in_response(
        self,
        user_id: str,
        response: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect if AI response contains a redundant question.
        
        Returns:
            (is_redundant, suggested_replacement)
        """
        response_lower = response.lower().strip()
        
        # Detect common redundant questions
        redundant_patterns = [
            (r"(where|which|what)\s+(location|city|place|area)", "location"),
            (r"what('s| is)\s+(your|ur)\s+name", "name"),
            (r"what\s+do\s+you\s+(like|prefer)", "preferences")
        ]
        
        for pattern, question_type in redundant_patterns:
            if re.search(pattern, response_lower):
                # Check if we have the answer
                check_result = await self.check_before_asking(
                    user_id, pattern, session_id, context
                )
                
                if check_result["have_answer"] and check_result["confidence"] >= 0.8:
                    # We have the answer - response is redundant
                    logger.warning(f"🚨 [Intelligence] Detected redundant question in response: {pattern}")
                    
                    # Generate suggested replacement
                    answer = check_result["answer"]
                    if question_type == "location":
                        replacement = f"Based on your location in {answer},"
                    elif question_type == "name":
                        replacement = f"{answer},"
                    elif question_type == "preferences":
                        replacement = f"Given your interests,"
                    else:
                        replacement = None
                    
                    return (True, replacement)
        
        return (False, None)


# Global instance
pre_response_intelligence = PreResponseIntelligence()


# Convenience functions
async def should_ask_question(
    user_id: str,
    question: str,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Check if we should ask a question"""
    return await pre_response_intelligence.check_before_asking(
        user_id, question, session_id, context
    )


async def check_response_for_redundancy(
    user_id: str,
    response: str,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]:
    """Check if response contains redundant questions"""
    return await pre_response_intelligence.detect_redundant_question_in_response(
        user_id, response, session_id, context
    )
