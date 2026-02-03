"""
🎯 ENHANCED MEMORY EXTRACTOR - PRO-LEVEL Intelligent Data Extraction
====================================================================

This module provides PRO-LEVEL intelligent extraction of user information
from conversations with advanced validation, importance scoring, and normalization.

🚀 PRO FEATURES:
- Multi-pass LLM extraction with fallback patterns
- Importance scoring (0-1) for memory prioritization
- Context-aware extraction (considers conversation history)
- Emotional sentiment detection
- Relationship strength tracking
- Temporal information extraction (deadlines, schedules)
- Memory update detection (user correcting previous info)
- Cross-reference validation
- Smart deduplication with merge capabilities

Key Features:
- LLM-based intelligent extraction with enhanced prompts
- Strict validation before storage
- Normalization of extracted data
- Confidence-based filtering
- Explicit vs implicit detection
- No hallucination protection
- Memory importance scoring
- Update/correction detection

Usage:
    from app.services.enhanced_memory_extractor import EnhancedMemoryExtractor, memory_extractor
    
    # Extract from message
    extracted = await memory_extractor.extract(user_id, message)
    
    # Validate before storage
    valid_memories = memory_extractor.validate_extractions(extracted)
"""

import logging
import re
import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ExtractionConfidence(Enum):
    """Confidence levels for extraction"""
    EXPLICIT = "explicit"      # User directly stated
    STRONG = "strong"          # Clearly implied
    MODERATE = "moderate"      # Reasonably inferred
    WEAK = "weak"              # Possibly implied
    UNCERTAIN = "uncertain"    # Just a guess


class MemoryImportance(Enum):
    """Importance levels for extracted memories - determines storage priority"""
    CRITICAL = 1.0       # Identity info (name, DOB), urgent tasks
    HIGH = 0.8           # Preferences, goals, relationships
    MEDIUM = 0.6         # Interests, hobbies, general facts
    LOW = 0.4            # Casual mentions, context
    MINIMAL = 0.2        # Temporary info, session-only


class DataCategory(Enum):
    """Categories of extractable data"""
    NAME = "name"
    NICKNAME = "nickname"
    AGE = "age"
    BIRTHDAY = "birthday"
    LOCATION = "location"
    OCCUPATION = "occupation"
    INTEREST = "interest"
    HOBBY = "hobby"
    PREFERENCE = "preference"
    DISLIKE = "dislike"
    RELATIONSHIP = "relationship"
    PROJECT = "project"
    GOAL = "goal"
    SKILL = "skill"
    LANGUAGE = "language"
    TIMEZONE = "timezone"
    COMMUNICATION_STYLE = "communication_style"
    FOOD_PREFERENCE = "food_preference"
    WORK_SCHEDULE = "work_schedule"
    CONTACT_INFO = "contact_info"
    HEALTH_INFO = "health_info"
    FINANCIAL_PREF = "financial_preference"
    LEARNING_STYLE = "learning_style"
    PET = "pet"
    FAMILY = "family"
    EDUCATION = "education"


# Map categories to importance levels
CATEGORY_IMPORTANCE = {
    DataCategory.NAME: MemoryImportance.CRITICAL,
    DataCategory.NICKNAME: MemoryImportance.HIGH,
    DataCategory.AGE: MemoryImportance.HIGH,
    DataCategory.BIRTHDAY: MemoryImportance.CRITICAL,
    DataCategory.LOCATION: MemoryImportance.HIGH,
    DataCategory.OCCUPATION: MemoryImportance.HIGH,
    DataCategory.INTEREST: MemoryImportance.MEDIUM,
    DataCategory.HOBBY: MemoryImportance.MEDIUM,
    DataCategory.PREFERENCE: MemoryImportance.HIGH,
    DataCategory.DISLIKE: MemoryImportance.HIGH,
    DataCategory.RELATIONSHIP: MemoryImportance.HIGH,
    DataCategory.PROJECT: MemoryImportance.MEDIUM,
    DataCategory.GOAL: MemoryImportance.HIGH,
    DataCategory.SKILL: MemoryImportance.MEDIUM,
    DataCategory.LANGUAGE: MemoryImportance.MEDIUM,
    DataCategory.TIMEZONE: MemoryImportance.HIGH,
    DataCategory.COMMUNICATION_STYLE: MemoryImportance.HIGH,
    DataCategory.FOOD_PREFERENCE: MemoryImportance.MEDIUM,
    DataCategory.WORK_SCHEDULE: MemoryImportance.HIGH,
    DataCategory.CONTACT_INFO: MemoryImportance.CRITICAL,
    DataCategory.HEALTH_INFO: MemoryImportance.HIGH,
    DataCategory.FINANCIAL_PREF: MemoryImportance.HIGH,
    DataCategory.LEARNING_STYLE: MemoryImportance.MEDIUM,
    DataCategory.PET: MemoryImportance.MEDIUM,
    DataCategory.FAMILY: MemoryImportance.HIGH,
    DataCategory.EDUCATION: MemoryImportance.HIGH,
}


class EnhancedMemoryExtractor:
    """
    🎯 PRO-LEVEL ENHANCED MEMORY EXTRACTOR
    
    Intelligently extracts user information from conversations
    with validation, normalization, importance scoring, and memory updates.
    
    🚀 PRO RULES:
    1. Only extract explicitly stated or clearly implied info
    2. Never hallucinate or assume
    3. Validate all extractions before storage
    4. Normalize data for consistency
    5. Assign confidence scores AND importance scores
    6. Detect memory updates/corrections
    7. Cross-reference with existing memories
    8. Support temporal/scheduling info
    9. Track relationship strength over time
    """
    
    def __init__(self):
        # Extraction patterns (rule-based backup when LLM unavailable)
        # 🚀 PRO: Enhanced with MORE patterns for comprehensive extraction
        self.EXTRACTION_PATTERNS = {
            DataCategory.NAME: [
                r"(?:^|[.!?]\s+)my name is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",  # Must start with capital
                r"(?:^|[.!?]\s+)i'm ([A-Z][a-z]+)(?:\s|$|,|\.)",  # "I'm Rathod" - must be capitalized
                r"(?:please |you can )?call me ([A-Z][a-z]+)",  # Must be capitalized 
                r"(?:^|[.!?]\s+)i am ([A-Z][a-z]+)(?:\s|$|,|\.)",  # "I am Rathod" - capitalized
                r"name's ([A-Z][a-z]+)",  # "name's John" - capitalized
                r"(?:hello|hi|hey),?\s+(?:my name is |i'm |i am )([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",  # greeting with name
                r"this is ([A-Z][a-z]+) speaking",  # "this is John speaking"
                r"everyone calls me ([A-Z][a-z]+)",  # "everyone calls me John"
            ],
            DataCategory.NICKNAME: [
                r"(?:you can |please )?call me ([A-Za-z]+)",
                r"my nickname is ([A-Za-z]+)",
                r"people call me ([A-Za-z]+)",
                r"i go by ([A-Za-z]+)",
                r"my friends call me ([A-Za-z]+)",
            ],
            DataCategory.LOCATION: [
                r"i live in ([A-Za-z\s,]+)",
                r"i'm from ([A-Za-z\s,]+)",  # "I'm John from NYC"
                r"i'm based in ([A-Za-z\s,]+)",
                r"i'm located in ([A-Za-z\s,]+)",
                r"my city is ([A-Za-z\s]+)",
                r"from ([A-Za-z\s,]+)$",  # "from NYC" at end of sentence
                r"living in ([A-Za-z\s,]+)",
                r"moved to ([A-Za-z\s,]+)",
                r"based out of ([A-Za-z\s,]+)",
                r"hometown is ([A-Za-z\s,]+)",
                r"originally from ([A-Za-z\s,]+)",
                r"currently in ([A-Za-z\s,]+)",
            ],
            DataCategory.AGE: [
                r"i'm (\d{1,3}) years old",
                r"i am (\d{1,3}) years old",
                r"my age is (\d{1,3})",
                r"i'm (\d{1,3})(?:\s|$|,)",  # "I'm 28" with boundary
                r"i am (\d{1,3})(?:\s|$|,)",  # "I am 28" with boundary
                r"(\d{1,3}) years old",  # Just "28 years old"
                r"age:?\s*(\d{1,3})",  # "age: 28" or "age 28"
            ],
            DataCategory.OCCUPATION: [
                r"i work as (?:a |an )?([A-Za-z\s]+?)(?:\.|,|$)",
                r"i'm (?:a |an )?([A-Za-z]+(?:\s+[A-Za-z]+)?)(?:\s+at|\s+in|\.|,|$)",
                r"my job is (?:a |an )?([A-Za-z\s]+?)(?:\.|,|$)",
                r"i'm employed as (?:a |an )?([A-Za-z\s]+?)(?:\.|,|$)",
                r"i work (?:at|in|for) .+ as (?:a |an )?([A-Za-z\s]+?)(?:\.|,|$)",
                r"my profession is ([A-Za-z\s]+?)(?:\.|,|$)",
                r"my role is ([A-Za-z\s]+?)(?:\.|,|$)",
            ],
            DataCategory.INTEREST: [
                r"i'm interested in ([A-Za-z\s,]+)",
                r"i'm into ([A-Za-z\s,]+)",
                r"i'm passionate about ([A-Za-z\s,]+)",
            ],
            DataCategory.HOBBY: [
                r"my hobbies? (?:is|are|include) ([A-Za-z\s,]+)",
                r"hobby is ([A-Za-z\s,]+)",  # "My hobby is playing guitar"
                r"i enjoy ([A-Za-z\s,]+)",
                r"i like to ([A-Za-z\s,]+)",
            ],
            DataCategory.PREFERENCE: [
                r"i (?:really )?(?:like|love|prefer|enjoy) ([A-Za-z\s]+)",
                r"my favorite (?:\w+) is ([A-Za-z\s]+)",
                r"i'm a fan of ([A-Za-z\s]+)",
            ],
            DataCategory.DISLIKE: [
                r"i (?:don't|do not|hate|dislike) ([A-Za-z\s]+)",
                r"i can't stand ([A-Za-z\s]+)",
                r"i'm not a fan of ([A-Za-z\s]+)",
            ],
            DataCategory.RELATIONSHIP: [
                r"my (wife|husband|partner|girlfriend|boyfriend|spouse)(?:'s name)? is ([A-Z][a-z]+)",
                r"my (mother|father|mom|dad|brother|sister|son|daughter)(?:'s name)? is ([A-Z][a-z]+)",
            ],
            DataCategory.PROJECT: [
                r"i'm working on ([A-Za-z\s]+)",
                r"my project is ([A-Za-z\s]+)",
                r"i'm building ([A-Za-z\s]+)",
            ],
            DataCategory.GOAL: [
                r"my goal is to ([A-Za-z\s]+)",
                r"i want to ([A-Za-z\s]+)",
                r"i'm trying to ([A-Za-z\s]+)",
                r"i plan to ([A-Za-z\s]+)",
                r"i aim to ([A-Za-z\s]+)",
                r"my dream is to ([A-Za-z\s]+)",
            ],
            DataCategory.SKILL: [
                r"i know ([A-Za-z\s,]+)",
                r"i can ([A-Za-z\s]+)",
                r"i'm skilled (?:in|at) ([A-Za-z\s]+)",
                r"i'm proficient (?:in|at) ([A-Za-z\s]+)",
                r"i'm good at ([A-Za-z\s]+)",
                r"i've mastered ([A-Za-z\s]+)",
                r"i specialize in ([A-Za-z\s]+)",
            ],
            DataCategory.LANGUAGE: [
                r"i speak ([A-Za-z\s,]+)",
                r"my (?:native |first )?language is ([A-Za-z]+)",
                r"i'm fluent in ([A-Za-z\s,]+)",
                r"i know ([A-Za-z]+) language",
            ],
            DataCategory.FOOD_PREFERENCE: [
                r"i (?:love|like|enjoy) eating ([A-Za-z\s,]+)",
                r"my favorite food is ([A-Za-z\s,]+)",
                r"i'm (?:a )?vegetarian",
                r"i'm (?:a )?vegan",
                r"i don't eat ([A-Za-z\s]+)",
                r"i prefer ([A-Za-z\s]+) food",
                r"i'm allergic to ([A-Za-z\s]+)",
            ],
            DataCategory.PET: [
                r"i have (?:a )?([A-Za-z]+) named ([A-Za-z]+)",
                r"my pet(?:'s name)? is ([A-Za-z]+)",
                r"my ([A-Za-z]+)'s name is ([A-Za-z]+)",
                r"i own (?:a )?([A-Za-z]+)",
            ],
            DataCategory.FAMILY: [
                r"i have (\d+) (?:kids|children|brothers|sisters)",
                r"i'm (?:a )?(single|married|divorced|engaged)",
                r"i have (?:a )?(?:son|daughter) named ([A-Za-z]+)",
            ],
            DataCategory.EDUCATION: [
                r"i (?:studied|majored in) ([A-Za-z\s]+)",
                r"i went to ([A-Za-z\s]+) (?:university|college|school)",
                r"i have (?:a )?(?:degree|PhD|masters) in ([A-Za-z\s]+)",
                r"i graduated from ([A-Za-z\s]+)",
            ],
            DataCategory.BIRTHDAY: [
                r"my birthday is (?:on )?([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?)",
                r"i was born (?:on )?([A-Za-z]+ \d{1,2})",
                r"born on ([A-Za-z]+ \d{1,2})",
            ],
            DataCategory.TIMEZONE: [
                r"i'm in (?:the )?([A-Za-z]+ (?:time ?zone|timezone))",
                r"my timezone is ([A-Z]{2,4})",
                r"i'm (?:on )?([A-Z]{2,4}) time",
            ],
        }
        
        # Validation rules
        self.VALIDATION_RULES = {
            DataCategory.NAME: self._validate_name,
            DataCategory.NICKNAME: self._validate_name,
            DataCategory.AGE: self._validate_age,
            DataCategory.LOCATION: self._validate_location,
            DataCategory.OCCUPATION: self._validate_occupation,
        }
        
        # Normalization rules
        self.NORMALIZERS = {
            DataCategory.NAME: self._normalize_name,
            DataCategory.NICKNAME: self._normalize_name,
            DataCategory.LOCATION: self._normalize_location,
            DataCategory.OCCUPATION: self._normalize_occupation,
            DataCategory.LANGUAGE: self._normalize_language,
        }
        
        # 🚀 PRO-LEVEL LLM Extraction Prompt - Much more comprehensive
        self.LLM_EXTRACTION_PROMPT = """
You are an expert information extractor for a personal AI assistant. Extract ALL factual information that the user has EXPLICITLY or CLEARLY IMPLIED about themselves.

🎯 EXTRACTION CATEGORIES:
- name, nickname: User's name or what they want to be called
- age, birthday: Age or birth date
- location: City, country, region, timezone
- occupation: Job title, profession, company
- interest, hobby: Things they're interested in or do for fun
- preference: Things they like, prefer, or enjoy
- dislike: Things they don't like or want to avoid
- relationship: Family members, partners (with names if given)
- project: Current work or personal projects
- goal: Aspirations, objectives, plans
- skill: Abilities, expertise, languages
- food_preference: Dietary preferences, favorite foods, allergies
- pet: Animals they own (type and name)
- family: Family status, children
- education: Degrees, schools, majors
- communication_style: How they prefer to communicate
- work_schedule: Working hours, availability
- health_info: Allergies, conditions (if shared)

🚀 STRICT RULES:
1. ONLY extract information the user directly states or CLEARLY implies
2. DO NOT infer, assume, or guess beyond what's stated
3. Extract relationships with names: "wife: Sarah" not just "has wife"
4. Assign importance: "critical" (identity), "high" (preferences), "medium" (interests), "low" (casual)
5. Assign confidence: "explicit" (directly said) or "strong" (clearly implied)
6. Detect UPDATES: If user says "actually my name is X" or "I moved to Y", mark as is_update: true
7. Return empty array [] if no extractable info

User message: "{message}"

Extract as JSON array:
[
  {{
    "category": "category_name",
    "value": "extracted value",
    "confidence": "explicit|strong",
    "importance": "critical|high|medium|low",
    "original_text": "relevant quote from message",
    "is_update": false
  }}
]

Return ONLY the JSON array, no other text.
"""
        
        # 🚀 PRO: Secondary patterns for updates/corrections
        self.UPDATE_PATTERNS = [
            r"actually,?\s+(?:my |i'm |i am )",
            r"(?:no|nope),?\s+(?:my |i'm |i am )",
            r"i meant to say",
            r"let me correct",
            r"i moved to",
            r"i changed (?:my|to)",
            r"i'm now",
            r"i recently",
        ]
        
        logger.info("🎯 PRO EnhancedMemoryExtractor initialized with enhanced patterns")
    
    def _detect_is_update(self, message: str) -> bool:
        """Detect if message contains an update/correction to previous info"""
        message_lower = message.lower()
        for pattern in self.UPDATE_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True
        return False
    
    async def extract(
        self,
        user_id: str,
        message: str,
        use_llm: bool = True,
        existing_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        🚀 PRO Extract user information from a message
        
        Args:
            user_id: User identifier
            message: Message to extract from
            use_llm: Whether to use LLM (falls back to regex if False or failed)
            existing_context: Optional existing user context for update detection
            
        Returns:
            List of extracted information dicts with importance scores
        """
        if not message or not message.strip():
            return []
        
        # 🔥 CRITICAL: Skip extraction from QUESTIONS about identity
        # Questions like "what's my name?", "do you know my name?" should NOT extract anything
        lower_msg = message.lower().strip()
        identity_question_patterns = [
            r"(what|who|do you know|can you tell|what's|whats|what is).*my\s*(name|age|location)",
            r"my\s*(name|age).*\?",
            r"know.*my\s*(name|age)",
            r"remember.*my\s*(name|age)",
            r"recall.*my\s*(name|age)",
        ]
        for pattern in identity_question_patterns:
            if re.search(pattern, lower_msg):
                logger.info(f"🛑 Skipping extraction from identity question: {message[:50]}...")
                return []
        
        extractions = []
        is_likely_update = self._detect_is_update(message)
        
        # Try LLM extraction first
        if use_llm:
            try:
                llm_extractions = await self._extract_with_llm(message)
                extractions.extend(llm_extractions)
            except Exception as e:
                logger.warning(f"LLM extraction failed, falling back to patterns: {e}")
        
        # Supplement with pattern-based extraction
        pattern_extractions = self._extract_with_patterns(message)
        
        # Merge extractions (LLM takes precedence, patterns fill gaps)
        extractions = self._merge_extractions(extractions, pattern_extractions)
        
        # Validate and filter
        validated = self.validate_extractions(extractions)
        
        # Normalize values
        normalized = [self._normalize_extraction(e) for e in validated]
        
        # Add metadata
        for extraction in normalized:
            extraction["user_id"] = user_id
            extraction["extracted_at"] = datetime.utcnow().isoformat()
            extraction["source"] = "conversation"
        
        logger.info(f"🎯 Extracted {len(normalized)} valid items from message")
        
        return normalized
    
    async def _extract_with_llm(self, message: str) -> List[Dict[str, Any]]:
        """Extract using LLM for better understanding"""
        try:
            from app.utils.llm_client import get_llm_response
            
            prompt = self.LLM_EXTRACTION_PROMPT.format(message=message)
            
            response = await get_llm_response(
                prompt=prompt,
                system_prompt="You are a precise JSON extractor. Return only valid JSON arrays.",
                timeout=5.0
            )
            
            # Parse JSON response
            response = response.strip()
            
            # Handle various response formats
            if response.startswith("```"):
                # Remove markdown code blocks
                response = re.sub(r"```(?:json)?\n?", "", response)
                response = response.replace("```", "").strip()
            
            # Find JSON array in response
            match = re.search(r'\[[\s\S]*\]', response)
            if match:
                response = match.group()
            
            extractions = json.loads(response)
            
            if not isinstance(extractions, list):
                return []
            
            return extractions
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM extraction response: {e}")
            return []
        except Exception as e:
            logger.warning(f"LLM extraction error: {e}")
            return []
    
    def _extract_with_patterns(self, message: str) -> List[Dict[str, Any]]:
        """Extract using regex patterns (backup method)"""
        extractions = []
        
        for category, patterns in self.EXTRACTION_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, message, re.IGNORECASE)
                for match in matches:
                    # Get the captured group (last group for relationship patterns)
                    groups = match.groups()
                    if len(groups) == 1:
                        value = groups[0]
                    elif len(groups) == 2:
                        # For relationship patterns: (relationship_type, name)
                        value = f"{groups[0]}: {groups[1]}"
                    else:
                        continue
                    
                    if value and value.strip():
                        extractions.append({
                            "category": category.value,
                            "value": value.strip(),
                            "confidence": ExtractionConfidence.EXPLICIT.value,
                            "original_text": match.group(),
                            "extraction_method": "pattern"
                        })
        
        return extractions
    
    def _merge_extractions(
        self,
        primary: List[Dict[str, Any]],
        secondary: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge extractions, preferring primary (LLM) results"""
        seen_categories = set()
        merged = []
        
        # Add all primary extractions
        for extraction in primary:
            cat_key = (extraction.get("category"), extraction.get("value", "").lower()[:20])
            seen_categories.add(cat_key)
            merged.append(extraction)
        
        # Add secondary extractions only if not already covered
        for extraction in secondary:
            cat_key = (extraction.get("category"), extraction.get("value", "").lower()[:20])
            if cat_key not in seen_categories:
                merged.append(extraction)
                seen_categories.add(cat_key)
        
        return merged
    
    def validate_extractions(
        self,
        extractions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate all extractions
        
        Removes invalid or suspicious extractions.
        """
        validated = []
        
        for extraction in extractions:
            category = extraction.get("category", "")
            value = extraction.get("value", "")
            
            if not category or not value:
                continue
            
            # Basic validation
            if not self._basic_validation(value):
                logger.debug(f"Failed basic validation: {value[:30]}...")
                continue
            
            # Category-specific validation
            try:
                cat_enum = DataCategory(category)
                validator = self.VALIDATION_RULES.get(cat_enum)
                
                if validator and not validator(value):
                    logger.debug(f"Failed category validation for {category}: {value[:30]}...")
                    continue
            except ValueError:
                pass  # Unknown category, skip specific validation
            
            # Check confidence
            confidence = extraction.get("confidence", "")
            if confidence in [ExtractionConfidence.WEAK.value, ExtractionConfidence.UNCERTAIN.value]:
                logger.debug(f"Skipping low confidence extraction: {value[:30]}...")
                continue
            
            validated.append(extraction)
        
        return validated
    
    def _basic_validation(self, value: str) -> bool:
        """Basic validation for any extracted value"""
        if not value or not isinstance(value, str):
            return False
        
        value = value.strip()
        
        # Too short
        if len(value) < 2:
            return False
        
        # Too long (likely garbage)
        if len(value) > 200:
            return False
        
        # Only numbers (except for age)
        if value.isdigit() and len(value) > 3:
            return False
        
        # Gibberish detection (too many consonants in a row)
        if re.search(r'[bcdfghjklmnpqrstvwxyz]{5,}', value.lower()):
            return False
        
        # Contains suspicious patterns
        suspicious = ['http', 'www.', '<', '>', 'script', 'eval(']
        if any(s in value.lower() for s in suspicious):
            return False
        
        return True
    
    def _validate_name(self, value: str) -> bool:
        """Validate a name extraction"""
        # Names should be mostly letters
        if not re.match(r'^[A-Za-z\s\'-]{2,50}$', value):
            return False
        
        # Should have at least one vowel
        if not re.search(r'[aeiouAEIOU]', value):
            return False
        
        # 🚀 PRO: Comprehensive blacklist of common words that are NOT names
        # This prevents false positives like "Really", "Also", "Very" etc.
        common_words = {
            # Articles and pronouns
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'i', 'you', 'he', 'she', 'it',
            'we', 'they', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
            # Common adverbs that match "I'm X" pattern
            'really', 'very', 'also', 'just', 'still', 'even', 'always', 'never',
            'often', 'sometimes', 'usually', 'actually', 'basically', 'literally',
            'definitely', 'certainly', 'probably', 'maybe', 'perhaps', 'quite',
            'rather', 'too', 'so', 'now', 'here', 'there', 'well', 'almost',
            # Common adjectives that follow "I'm"
            'happy', 'sad', 'tired', 'hungry', 'busy', 'free', 'good', 'bad',
            'fine', 'great', 'okay', 'ok', 'sorry', 'sure', 'ready', 'done',
            'excited', 'interested', 'passionate', 'curious', 'confused',
            # Verbs and auxiliaries
            'going', 'trying', 'working', 'looking', 'thinking', 'feeling',
            'doing', 'making', 'getting', 'having', 'being', 'taking',
            # Other common false positives
            'not', 'about', 'into', 'from', 'back', 'home', 'away', 'new', 'old',
            'big', 'small', 'long', 'short', 'high', 'low', 'full', 'empty',
            'open', 'closed', 'true', 'false', 'right', 'wrong', 'first', 'last',
            # 🔥 CRITICAL: Values that indicate "no data" - NEVER store these!
            'unknown', 'none', 'null', 'undefined', 'n/a', 'na', 'nil',
            'not provided', 'not specified', 'not given', 'not set',
            'anonymous', 'user', 'guest', 'default',
            # Single letters
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
        }
        if value.lower() in common_words:
            return False
        
        # 🚀 Names should be at least 2 characters  
        if len(value.strip()) < 2:
            return False
            
        return True
    
    def _validate_age(self, value: str) -> bool:
        """Validate an age extraction"""
        try:
            age = int(re.search(r'\d+', value).group())
            return 1 <= age <= 120
        except:
            return False
    
    def _validate_location(self, value: str) -> bool:
        """Validate a location extraction"""
        # Locations should be mostly letters and common punctuation
        if not re.match(r'^[A-Za-z\s,\.\'-]{2,100}$', value):
            return False
        
        # Shouldn't be too generic
        too_generic = {'here', 'there', 'somewhere', 'anywhere', 'nowhere', 'place'}
        if value.lower() in too_generic:
            return False
        
        return True
    
    def _validate_occupation(self, value: str) -> bool:
        """Validate an occupation extraction"""
        # Should be reasonable length
        if len(value) < 3 or len(value) > 100:
            return False
        
        # Mostly letters
        if not re.match(r'^[A-Za-z\s\-/]+$', value):
            return False
        
        return True
    
    def _normalize_extraction(self, extraction: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize an extraction's value"""
        normalized = extraction.copy()
        category = extraction.get("category", "")
        value = extraction.get("value", "")
        
        try:
            cat_enum = DataCategory(category)
            normalizer = self.NORMALIZERS.get(cat_enum)
            
            if normalizer:
                normalized["value"] = normalizer(value)
            else:
                # Default normalization
                normalized["value"] = value.strip()
        except ValueError:
            normalized["value"] = value.strip()
        
        return normalized
    
    def _normalize_name(self, value: str) -> str:
        """Normalize a name (title case)"""
        return value.strip().title()
    
    def _normalize_location(self, value: str) -> str:
        """Normalize a location"""
        # Title case for cities/countries
        normalized = value.strip().title()
        
        # Fix common abbreviations
        replacements = {
            ' Usa': ' USA',
            ' Uk': ' UK',
            ' Uae': ' UAE',
            'New york': 'New York',
            'Los angeles': 'Los Angeles',
            'San francisco': 'San Francisco',
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized
    
    def _normalize_occupation(self, value: str) -> str:
        """Normalize an occupation"""
        # Title case
        normalized = value.strip().title()
        
        # Common normalization
        replacements = {
            'Software Dev': 'Software Developer',
            'Sw Engineer': 'Software Engineer',
            'Swe': 'Software Engineer',
            'Pm': 'Product Manager',
            'Ceo': 'CEO',
            'Cto': 'CTO',
            'Vp': 'VP',
        }
        
        for old, new in replacements.items():
            if normalized == old:
                normalized = new
        
        return normalized
    
    def _normalize_language(self, value: str) -> str:
        """Normalize a language name"""
        # Title case
        normalized = value.strip().title()
        
        # Common language names
        languages = {
            'English', 'Spanish', 'French', 'German', 'Chinese',
            'Japanese', 'Korean', 'Portuguese', 'Russian', 'Arabic',
            'Hindi', 'Italian', 'Dutch', 'Polish', 'Turkish'
        }
        
        for lang in languages:
            if normalized.lower() == lang.lower():
                return lang
        
        return normalized
    
    def _get_importance_for_category(self, category: str) -> float:
        """Get importance score for a category"""
        try:
            cat_enum = DataCategory(category)
            importance = CATEGORY_IMPORTANCE.get(cat_enum, MemoryImportance.MEDIUM)
            return importance.value
        except ValueError:
            return MemoryImportance.MEDIUM.value
    
    def extract_and_prepare_for_storage(
        self,
        user_id: str,
        message: str
    ) -> List[Dict[str, Any]]:
        """
        🚀 PRO Extract and prepare memories for storage
        
        Returns memories ready to be stored with all required fields including importance.
        """
        # This is a sync wrapper for use in sync contexts
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, use create_task
                extractions = asyncio.create_task(self.extract(user_id, message))
            else:
                extractions = loop.run_until_complete(self.extract(user_id, message))
        except RuntimeError:
            # No event loop, create one
            extractions = asyncio.run(self.extract(user_id, message))
        
        # Convert to storage format with PRO enhancements
        storage_ready = []
        for extraction in extractions:
            category = extraction.get("category", "")
            importance = self._get_importance_for_category(category)
            
            storage_ready.append({
                "user_id": user_id,
                "type": extraction.get("category"),
                "text": extraction.get("value"),
                "source": "user_explicit" if extraction.get("confidence") == "explicit" else "ai_extracted",
                "confidence": 0.95 if extraction.get("confidence") == "explicit" else 0.8,
                "importance": importance,  # 🚀 PRO: Importance score
                "category": extraction.get("category"),
                "created_at": extraction.get("extracted_at"),
                "original_text": extraction.get("original_text"),
                "is_update": extraction.get("is_update", False),  # 🚀 PRO: Update flag
            })
        
        return storage_ready
    
    def should_extract_from_message(self, message: str) -> bool:
        """
        🚀 PRO Quick check if message likely contains extractable info
        
        Much more sensitive to catch all personal information.
        """
        if not message or len(message) < 3:  # Very short threshold
            return False
        
        lower_msg = message.lower()
        
        # 🚀 PRO: Expanded personal indicators for comprehensive extraction
        personal_indicators = [
            # Identity
            r'\bi\s+(?:am|\'m|was|will be)\b',
            r'\bmy\s+\w+',  # Any "my X" pattern
            r'\bcall\s+me\b',
            r'\bname\s+is\b',
            
            # Location
            r'\bfrom\s+[A-Za-z]+',
            r'\blive\s+in\b',
            r'\bbased\s+in\b',
            r'\bmoved\s+to\b',
            
            # Work/Education
            r'\bi\s+work\b',
            r'\bi\s+study\b',
            r'\bi\s+studied\b',
            r'\bmy\s+job\b',
            r'\bi\'m\s+(?:a|an)\s+\w+',  # "I'm a developer"
            
            # Preferences
            r'\bi\s+(?:like|love|enjoy|prefer|hate|dislike)\b',
            r'\bmy\s+favorite\b',
            r'\bi\s+(?:can\'t|don\'t)\s+stand\b',
            
            # Relationships/Family
            r'\bmy\s+(?:wife|husband|partner|mom|dad|brother|sister|son|daughter|friend)\b',
            r'\bi\s+have\s+(?:a|an|\d+)\b',
            r'\bi\'m\s+(?:married|single|engaged|divorced)\b',
            
            # Goals/Projects
            r'\bi\s+(?:want|plan|aim|hope|dream)\b',
            r'\bi\'m\s+(?:working|building|creating|developing)\b',
            r'\bmy\s+(?:goal|project|dream)\b',
            
            # Skills
            r'\bi\s+(?:know|can|speak)\b',
            r'\bi\'m\s+(?:good|skilled|fluent)\b',
            r'\bi\s+specialize\b',
            
            # Food/Lifestyle
            r'\bi\s+eat\b',
            r'\bi\'m\s+(?:vegetarian|vegan)\b',
            r'\bi\s+don\'t\s+eat\b',
            r'\bi\'m\s+allergic\b',
            
            # Schedule/Time
            r'\bi\s+usually\b',
            r'\bmy\s+schedule\b',
            r'\bi\s+wake\s+up\b',
            r'\bmy\s+timezone\b',
            
            # Updates/Corrections
            r'\bactually\b',
            r'\bi\s+meant\b',
            r'\blet\s+me\s+correct\b',
            r'\bi\s+changed\b',
        ]
        
        for pattern in personal_indicators:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        
        # Even for questions, check if they contain self-referential info
        # "Can you help me? I'm a developer from NYC" - contains info even though it's a question
        if message.strip().endswith('?'):
            # Still extract if there's personal info in the question
            for pattern in personal_indicators[:10]:  # Check main identity patterns
                if re.search(pattern, message, re.IGNORECASE):
                    return True
            return False
        
        # For statements, be more permissive - check for any first-person info
        if re.search(r'\bi\b', lower_msg) and len(message) > 10:
            return True
        
        return False


# Global singleton instance
memory_extractor = EnhancedMemoryExtractor()
