"""
🎯 User Detail Extraction Service

Intelligently extracts user details from chat messages using LLM.
Runs in parallel with response generation - never blocks the chat pipeline.

Extracts:
- Personal info (name, age, location, occupation)
- Interests & hobbies
- Preferences & dislikes
- Goals & aspirations
- Relationships & family
- And more...
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from bson import ObjectId

from app.utils.llm_client import get_llm_response
from app.db.mongo_client import users_collection, memory_collection
from app.db.neo4j_client import graph_memory
from app.services.vector_memory_service import get_vector_memory

logger = logging.getLogger(__name__)


class UserDetailExtractor:
    """
    🎯 Intelligent User Detail Extraction
    
    Uses LLM to extract structured user information from natural language.
    All updates happen in background - never blocks chat responses.
    """
    
    def __init__(self):
        self.extraction_cache = {}  # Cache recent extractions to avoid duplicates
    
    async def extract_user_details(
        self,
        user_id: str,
        message: str,
        ai_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract user details from message and AI response.
        
        Returns structured data ready for storage.
        Runs in background - doesn't block chat pipeline.
        """
        try:
            logger.info(f"✅ [Step] Extraction started for user: {user_id}")
            logger.info(f"✅ [Step] Raw user input: {message[:100]}...")
            
            # Check cache to avoid duplicate processing
            message_hash = hash(f"{user_id}:{message[:100]}")
            if message_hash in self.extraction_cache:
                logger.debug(f"⏭️ Skipping duplicate extraction for message hash: {message_hash}")
                logger.info(f"✅ [Step] Duplicate extraction skipped (cached)")
                return self.extraction_cache[message_hash]
            
            logger.info(f"🔍 Extracting user details from message for user: {user_id}")
            
            # STRICT: Use ONLY raw user message for extraction; ignore AI response
            if ai_response:
                logger.debug("ℹ️ Ignoring AI response for extraction per strict policy")
                logger.info(f"✅ [Step] AI response ignored (raw-only extraction policy)")
            extraction_prompt = self._build_extraction_prompt(message, None)
            
            # Get LLM extraction (with timeout to not block)
            try:
                logger.info(f"✅ [Step] Calling LLM for extraction")
                extraction_result = await get_llm_response(
                    prompt=extraction_prompt,
                    system_prompt=self._get_extraction_system_prompt(),
                    timeout=5.0  # 5 second timeout - don't block chat
                )
                logger.info(f"✅ [Step] LLM extraction completed")
            except Exception as e:
                logger.warning(f"⚠️ Extraction LLM call failed: {e}")
                logger.error(f"❌ [Step] Extraction LLM failed: {e}")
                return {"extracted": False, "error": str(e)}
            
            # Parse extraction result
            logger.info(f"✅ [Step] Parsing extraction result")
            extracted_data = self._parse_extraction_result(extraction_result)
            
            if extracted_data.get("extracted"):
                # Cache result
                self.extraction_cache[message_hash] = extracted_data
                # Clear cache after 100 entries to prevent memory leak
                if len(self.extraction_cache) > 100:
                    self.extraction_cache.clear()
                
                logger.info(f"✅ Extracted {len(extracted_data.get('data', {}))} user details")
                logger.info(f"✅ [Step] Extraction successful - {len(extracted_data.get('data', {}))} fields extracted")
                return extracted_data
            else:
                logger.debug("ℹ️ No extractable details found in message")
                logger.info(f"✅ [Step] No extractable details found")
                return {"extracted": False, "reason": "no_details_found"}
                
        except Exception as e:
            logger.error(f"❌ Error extracting user details: {e}")
            return {"extracted": False, "error": str(e)}
    
    def _build_extraction_prompt(self, message: str, ai_response: Optional[str] = None) -> str:
        """Build STRICT prompt: extract ONLY from raw user input"""
        prompt = f"""
🎯 STRICT USER DETAIL EXTRACTION

Extract ONLY explicit personal details stated by the user.
Do NOT infer, expand, or guess. No assistant text.

=== USER MESSAGE ===
{message}

"""
        # Ignore ai_response entirely by policy
        
        prompt += """
=== EXTRACTION REQUIREMENTS ===

Extract the following information ONLY if EXPLICITLY mentioned:

1. PERSONAL INFORMATION
   - Full name, nickname, preferred name
   - Age, birthday, birth date
   - Location (city, country, timezone)
   - Occupation, job title, profession
   - Education level, school, university
   - Gender, pronouns
   - Language preferences

2. INTERESTS & HOBBIES
   - Topics of interest (AI, technology, sports, etc.)
   - Hobbies and activities
   - Favorite subjects or fields
   - Passions and enthusiasms

3. PREFERENCES & TASTES
   - Likes and favorites (food, music, movies, books, etc.)
   - Dislikes and aversions
   - Style preferences
   - Communication preferences
   - Work preferences

4. GOALS & ASPIRATIONS
   - Short-term goals
   - Long-term aspirations
   - Career objectives
   - Personal development goals
   - Dreams and ambitions

5. RELATIONSHIPS
   - Family members (spouse, children, parents, siblings)
   - Friends and social connections
   - Pets and animals
   - Professional relationships

6. LIFESTYLE
   - Daily habits and routines
   - Sleep schedule
   - Exercise routines
   - Eating habits
   - Work schedule
   - Travel patterns

7. SKILLS & EXPERTISE
   - Technical skills
   - Soft skills
   - Languages spoken
   - Certifications
   - Areas of expertise

8. PERSONALITY TRAITS
   - Communication style
   - Work style
   - Social preferences
   - Learning style
   - Decision-making style

9. CONTEXT & SITUATION
   - Current projects
   - Recent events
   - Challenges faced
   - Achievements
   - Current mood or state

=== OUTPUT FORMAT ===

Return ONLY valid JSON with this exact structure:

{
  "extracted": true,
  "data": {
    "personal_info": {
      "name": "string or null",
      "age": "string or null",
      "location": "string or null",
      "occupation": "string or null",
      "education": "string or null",
      "gender": "string or null",
      "pronouns": "string or null",
      "languages": ["string"],
      "timezone": "string or null"
    },
    "interests": ["string"],
    "hobbies": ["string"],
    "preferences": {
      "likes": ["string"],
      "dislikes": ["string"],
      "favorites": {
        "food": ["string"],
        "music": ["string"],
        "movies": ["string"],
        "books": ["string"],
        "activities": ["string"]
      }
    },
    "goals": ["string"],
    "relationships": {
      "family": ["string"],
      "friends": ["string"],
      "pets": ["string"]
    },
    "lifestyle": {
      "habits": ["string"],
      "routines": ["string"],
      "schedule": "string or null"
    },
    "skills": ["string"],
    "personality": {
      "traits": ["string"],
      "communication_style": "string or null",
      "work_style": "string or null"
    },
    "context": {
      "current_projects": ["string"],
      "recent_events": ["string"],
      "challenges": ["string"],
      "achievements": ["string"]
    }
  },
  "confidence": 0.0-1.0,
  "extraction_notes": "Brief notes about what was extracted"
}

If NO extractable information is found, return:
{
  "extracted": false,
  "reason": "no_details_found",
  "confidence": 0.0
}

=== EXTRACTION RULES ===
1. Only extract EXPLICITLY stated information
2. Extract CLEARLY IMPLIED information (e.g., "I'm a developer" → occupation: "developer")
3. Do NOT make assumptions or infer details
4. Preserve original wording when possible
5. Use arrays for multiple values
6. Use null for missing fields (not empty strings)
7. Be thorough - extract everything mentioned
8. Confidence should reflect certainty (0.9+ for explicit, 0.6-0.8 for implied)

=== EXAMPLES ===

User: "Hi, I'm John, a software engineer from New York. I love Python and hiking."
Extract:
{
  "extracted": true,
  "data": {
    "personal_info": {"name": "John", "occupation": "software engineer", "location": "New York"},
    "interests": ["Python programming"],
    "hobbies": ["hiking"]
  },
  "confidence": 0.95
}

Now extract from the conversation above:
"""
        return prompt
    
    def _get_extraction_system_prompt(self) -> str:
        """Enhanced system prompt for extraction LLM"""
        return """You are an expert information extraction system specialized in extracting structured user details from natural language conversations.

Your primary goal is to extract ALL relevant personal information, preferences, and details that the user shares.

EXTRACTION PRINCIPLES:
1. Be THOROUGH - Extract everything mentioned, not just obvious facts
2. Be PRECISE - Only extract what is explicitly stated or clearly implied
3. Be STRUCTURED - Always return valid JSON matching the exact format
4. Be CONFIDENT - Assign appropriate confidence scores (0.9+ for explicit, 0.6-0.8 for implied)
5. Preserve CONTEXT - Keep original wording and context when possible
6. Handle MULTIPLE VALUES - Use arrays for lists, objects for structured data
7. Be CONSISTENT - Use the same field names and structure every time

QUALITY STANDARDS:
- Extract even subtle mentions (e.g., "I usually work late" → lifestyle.habits)
- Capture relationships and connections
- Note preferences even if not explicitly stated as "I like..."
- Extract goals and aspirations mentioned in passing
- Capture personality traits from communication style
- Note current context and situation

OUTPUT REQUIREMENTS:
- Always return valid JSON
- Use null for missing fields (never empty strings)
- Use arrays for multiple values
- Include confidence score
- Add extraction_notes for context

Remember: Your extraction enables personalized AI experiences. Be thorough and accurate.
"""
    
    def _parse_extraction_result(self, result: str) -> Dict[str, Any]:
        """Parse LLM extraction result into structured data"""
        try:
            # Try to find JSON in the response
            result = result.strip()
            
            # Remove markdown code blocks if present
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            parsed = json.loads(result)
            
            # Validate structure
            if isinstance(parsed, dict) and "extracted" in parsed:
                return parsed
            else:
                logger.warning(f"⚠️ Invalid extraction result structure: {parsed}")
                return {"extracted": False, "reason": "invalid_structure"}
                
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Failed to parse extraction JSON: {e}")
            logger.debug(f"Raw result: {result[:200]}")
            return {"extracted": False, "reason": "json_parse_error"}
        except Exception as e:
            logger.error(f"❌ Error parsing extraction result: {e}")
            return {"extracted": False, "error": str(e)}
    
    async def save_extracted_details(
        self,
        user_id: str,
        extracted_data: Dict[str, Any],
        source_message: str
    ) -> Dict[str, bool]:
        """
        Save extracted details to all memory systems in parallel.
        
        Returns status of each storage operation.
        All operations run in background - non-blocking.
        """
        if not extracted_data.get("extracted"):
            return {"saved": False, "reason": extracted_data.get("reason", "no_data")}
        
        data = extracted_data.get("data", {})
        results = {"mongodb": False, "neo4j": False, "vector": False, "redis": False, "atomic_saved": False}

        # Pre-validate availability to enforce atomicity (all-or-nothing)
        try:
            neo4j_ok = True  # graph_memory methods are async wrappers; driver availability handled inside
            vm = get_vector_memory()
            vector_ok = bool(vm and vm.index)
            if not vector_ok:
                logger.warning("⚠️ Vector memory unavailable; aborting atomic memory save")
                return results
        except Exception as e:
            logger.warning(f"⚠️ Precheck failed; aborting atomic memory save: {e}")
            return results

        try:
            logger.info(f"✅ [Step] Starting atomic save sequence for user: {user_id}")
            
            # Sequence writes; only proceed if each succeeds
            logger.info(f"✅ [Step] Saving to Neo4j...")
            neo4j_res = await self._save_to_neo4j(user_id, data, source_message) if neo4j_ok else False
            if not neo4j_res:
                logger.warning("⚠️ Neo4j save failed; aborting memory save (all-or-nothing)")
                logger.error(f"❌ [Step] Neo4j save failed - atomic save aborted")
                return results
            results["neo4j"] = True
            logger.info(f"✅ [Step] Neo4j save successful")

            logger.info(f"✅ [Step] Saving to Vector store...")
            vector_res = await self._save_to_vector(user_id, data, source_message)
            if not vector_res:
                logger.warning("⚠️ Vector save failed; aborting memory save (all-or-nothing)")
                logger.error(f"❌ [Step] Vector save failed - atomic save aborted")
                return results
            results["vector"] = True
            logger.info(f"✅ [Step] Vector save successful")

            logger.info(f"✅ [Step] Saving to MongoDB...")
            mongo_res = await self._save_to_mongodb(user_id, data, source_message)
            if not mongo_res:
                logger.warning("⚠️ MongoDB save failed; aborting memory save (all-or-nothing)")
                logger.error(f"❌ [Step] MongoDB save failed - atomic save aborted")
                return results
            results["mongodb"] = True
            logger.info(f"✅ [Step] MongoDB save successful")

            # Redis is optional cache; do not block atomic result on cache errors
            try:
                results["redis"] = await self._save_to_redis(user_id, data)
            except Exception:
                results["redis"] = False

            results["atomic_saved"] = True
            logger.info("✅ [Atomic] Extracted details saved across MongoDB + Neo4j + Vector")
            logger.info(f"✅ [Step] Atomic save complete - MongoDB: {results['mongodb']}, Neo4j: {results['neo4j']}, Vector: {results['vector']}")

            # 🔄 Invalidate caches after successful atomic save to prevent stale recall
            try:
                from app.services.cache_service import cache_service
                await cache_service.invalidate_keys([
                    f"history:{user_id}",
                    f"highlights:{user_id}",
                    f"miniagents:{user_id}",
                ])
                logger.info("[Cache] Invalidated after atomic memory save")
                logger.info(f"✅ [Step] Cache invalidated for user: {user_id}")
            except Exception as e:
                logger.warning(f"[Cache] Invalidation error after memory save: {e}")

            return results
        except Exception as e:
            logger.error(f"❌ Error saving extracted details atomically: {e}")
            return results
    
    async def _save_to_mongodb(
        self,
        user_id: str,
        data: Dict[str, Any],
        source_message: str
    ) -> bool:
        """Save extracted details to MongoDB"""
        try:
            user_obj_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else None
            if not user_obj_id:
                return False
            
            # Update user profile
            update_fields = {}
            
            # Personal info (comprehensive extraction)
            if "personal_info" in data:
                personal = data["personal_info"]
                if personal.get("name"):
                    update_fields["name"] = personal["name"]
                    update_fields["profile.name"] = personal["name"]
                if personal.get("age"):
                    update_fields["profile.age"] = personal["age"]
                if personal.get("location"):
                    update_fields["profile.location"] = personal["location"]
                if personal.get("occupation"):
                    update_fields["profile.occupation"] = personal["occupation"]
                if personal.get("education"):
                    update_fields["profile.education"] = personal["education"]
                if personal.get("gender"):
                    update_fields["profile.gender"] = personal["gender"]
                if personal.get("pronouns"):
                    update_fields["profile.pronouns"] = personal["pronouns"]
                if personal.get("timezone"):
                    update_fields["profile.timezone"] = personal["timezone"]
                if personal.get("languages"):
                    update_fields["$addToSet"] = {"profile.languages": {"$each": personal["languages"]}}
            
            # Initialize $addToSet if needed
            add_to_set_fields = {}
            
            # Interests
            if "interests" in data and data["interests"]:
                add_to_set_fields["interests"] = {"$each": data["interests"]}
                add_to_set_fields["profile.interests"] = {"$each": data["interests"]}
            
            # Hobbies
            if "hobbies" in data and data["hobbies"]:
                add_to_set_fields["profile.hobbies"] = {"$each": data["hobbies"]}
            
            # Preferences
            if "preferences" in data:
                prefs = data["preferences"]
                if prefs.get("likes"):
                    add_to_set_fields["profile.preferences.likes"] = {"$each": prefs["likes"]}
                if prefs.get("dislikes"):
                    add_to_set_fields["profile.preferences.dislikes"] = {"$each": prefs["dislikes"]}
                if prefs.get("favorites"):
                    update_fields["profile.favorites"] = prefs["favorites"]
            
            # Goals
            if "goals" in data and data["goals"]:
                add_to_set_fields["profile.goals"] = {"$each": data["goals"]}
            
            # Skills
            if "skills" in data and data["skills"]:
                add_to_set_fields["profile.skills"] = {"$each": data["skills"]}
            
            # Personality traits
            if "personality" in data:
                personality = data["personality"]
                if personality.get("traits"):
                    add_to_set_fields["profile.personality.traits"] = {"$each": personality["traits"]}
                if personality.get("communication_style"):
                    update_fields["profile.personality.communication_style"] = personality["communication_style"]
                if personality.get("work_style"):
                    update_fields["profile.personality.work_style"] = personality["work_style"]
            
            # Add $addToSet to update_fields if we have any
            if add_to_set_fields:
                update_fields["$addToSet"] = add_to_set_fields
            
            # Update user document with proper field handling
            if update_fields:
                # Separate $set and $addToSet operations
                set_fields = {k: v for k, v in update_fields.items() if not k.startswith("$")}
                add_to_set_ops = {}
                
                # Handle $addToSet operations properly
                if "$addToSet" in update_fields:
                    add_to_set_ops = update_fields["$addToSet"]
                
                update_operation = {}
                if set_fields:
                    update_operation["$set"] = set_fields
                if add_to_set_ops:
                    update_operation["$addToSet"] = add_to_set_ops
                
                if update_operation:
                    await users_collection.update_one(
                        {"_id": user_obj_id},
                        update_operation,
                        upsert=False  # Don't create user if doesn't exist
                    )
            
            # Save to memory collection
            memory_doc = {
                "userId": user_obj_id,
                "type": "extracted_details",
                "source": source_message,
                "data": data,
                "extracted_at": datetime.utcnow(),
                "confidence": data.get("confidence", 0.5)
            }
            
            await memory_collection.insert_one(memory_doc)
            
            logger.info(f"✅ MongoDB: Extracted details saved for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ MongoDB save error: {e}")
            return False
    
    async def _save_to_neo4j(
        self,
        user_id: str,
        data: Dict[str, Any],
        source_message: str
    ) -> bool:
        """Save extracted details to Neo4j graph"""
        try:
            # Personal info (comprehensive)
            if "personal_info" in data:
                personal = data["personal_info"]
                if personal.get("name"):
                    await graph_memory.update_user_name(user_id, personal["name"])
                if personal.get("location"):
                    await graph_memory.add_user_property(user_id, "location", personal["location"])
                if personal.get("occupation"):
                    await graph_memory.add_user_property(user_id, "occupation", personal["occupation"])
                if personal.get("age"):
                    await graph_memory.add_user_property(user_id, "age", personal["age"])
                if personal.get("education"):
                    await graph_memory.add_user_property(user_id, "education", personal["education"])
            
            # Interests
            if "interests" in data:
                for interest in data["interests"]:
                    await graph_memory.add_interest_relationship(user_id, interest, "interest")
            
            # Hobbies
            if "hobbies" in data:
                for hobby in data["hobbies"]:
                    await graph_memory.add_interest_relationship(user_id, hobby, "hobby")
            
            # Goals
            if "goals" in data:
                for goal in data["goals"]:
                    await graph_memory.add_interest_relationship(user_id, goal, "goal")
            
            # Skills
            if "skills" in data:
                for skill in data["skills"]:
                    await graph_memory.add_interest_relationship(user_id, skill, "skill")
            
            # Preferences (likes)
            if "preferences" in data and data["preferences"].get("likes"):
                for like in data["preferences"]["likes"]:
                    await graph_memory.add_interest_relationship(user_id, like, "preference")
            
            # Relationships
            if "relationships" in data:
                rels = data["relationships"]
                if rels.get("family"):
                    for family_member in rels["family"]:
                        await graph_memory.add_interest_relationship(user_id, family_member, "family")
                if rels.get("pets"):
                    for pet in rels["pets"]:
                        await graph_memory.add_interest_relationship(user_id, pet, "pet")
            
            logger.info(f"✅ Neo4j: Extracted details saved for user {user_id}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Neo4j save error: {e}")
            return False
    
    async def _save_to_vector(
        self,
        user_id: str,
        data: Dict[str, Any],
        source_message: str
    ) -> bool:
        """Save extracted details to vector database (comprehensive)"""
        try:
            # Create a comprehensive text representation
            text_parts = []
            
            # Personal info
            if "personal_info" in data:
                personal = data["personal_info"]
                personal_text = []
                for key, value in personal.items():
                    if value:
                        personal_text.append(f"{key.replace('_', ' ')}: {value}")
                if personal_text:
                    text_parts.append(f"Personal information: {'; '.join(personal_text)}")
            
            # Interests
            if "interests" in data and data["interests"]:
                text_parts.append(f"Interests: {', '.join(data['interests'])}")
            
            # Hobbies
            if "hobbies" in data and data["hobbies"]:
                text_parts.append(f"Hobbies: {', '.join(data['hobbies'])}")
            
            # Goals
            if "goals" in data and data["goals"]:
                text_parts.append(f"Goals: {', '.join(data['goals'])}")
            
            # Skills
            if "skills" in data and data["skills"]:
                text_parts.append(f"Skills: {', '.join(data['skills'])}")
            
            # Preferences
            if "preferences" in data:
                prefs = data["preferences"]
                pref_text = []
                if prefs.get("likes"):
                    pref_text.append(f"Likes: {', '.join(prefs['likes'])}")
                if prefs.get("dislikes"):
                    pref_text.append(f"Dislikes: {', '.join(prefs['dislikes'])}")
                if pref_text:
                    text_parts.append('; '.join(pref_text))
            
            # Relationships
            if "relationships" in data:
                rels = data["relationships"]
                rel_text = []
                if rels.get("family"):
                    rel_text.append(f"Family: {', '.join(rels['family'])}")
                if rels.get("pets"):
                    rel_text.append(f"Pets: {', '.join(rels['pets'])}")
                if rel_text:
                    text_parts.append('; '.join(rel_text))
            
            # Lifestyle
            if "lifestyle" in data:
                lifestyle = data["lifestyle"]
                lifestyle_text = []
                if lifestyle.get("habits"):
                    lifestyle_text.append(f"Habits: {', '.join(lifestyle['habits'])}")
                if lifestyle.get("routines"):
                    lifestyle_text.append(f"Routines: {', '.join(lifestyle['routines'])}")
                if lifestyle_text:
                    text_parts.append('; '.join(lifestyle_text))
            
            # Personality
            if "personality" in data and data["personality"].get("traits"):
                text_parts.append(f"Personality: {', '.join(data['personality']['traits'])}")
            
            # Context
            if "context" in data:
                ctx = data["context"]
                ctx_text = []
                if ctx.get("current_projects"):
                    ctx_text.append(f"Projects: {', '.join(ctx['current_projects'])}")
                if ctx.get("achievements"):
                    ctx_text.append(f"Achievements: {', '.join(ctx['achievements'])}")
                if ctx_text:
                    text_parts.append('; '.join(ctx_text))
            
            if text_parts:
                combined_text = f"User profile: {' | '.join(text_parts)}"
                vm = get_vector_memory()
                await vm.add_memory(user_id, combined_text, metadata={
                    "type": "extracted_details",
                    "source": source_message,
                    "extracted_at": datetime.utcnow().isoformat(),
                    "comprehensive": True
                })
            
            logger.info(f"✅ Vector: Extracted details saved for user {user_id}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Vector save error: {e}")
            return False
    
    async def _save_to_redis(
        self,
        user_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """Cache extracted details in Redis"""
        try:
            from app.db.redis_client import redis_client
            
            cache_key = f"user_details:{user_id}"
            await redis_client.setex(
                cache_key,
                3600,  # 1 hour TTL
                json.dumps(data)
            )
            
            logger.debug(f"✅ Redis: Extracted details cached for user {user_id}")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Redis cache error: {e}")
            return False


# Global instance
user_detail_extractor = UserDetailExtractor()


# Convenience function for background tasks
async def extract_and_save_user_details_async(
    user_id: str,
    message: str,
    ai_response: Optional[str] = None
):
    """
    🚀 Background task: Extract and save user details.
    
    Call this AFTER sending chat response - never blocks the pipeline.
    """
    try:
        # Extract details from RAW user message ONLY (ai_response ignored)
        extracted = await user_detail_extractor.extract_user_details(
            user_id,
            message,
            None
        )
        
        # Save if extraction successful; acknowledge only if atomic save succeeds
        if extracted.get("extracted"):
            logger.info(f"✅ [Step] Starting atomic save for extracted details")
            save_results = await user_detail_extractor.save_extracted_details(
                user_id,
                extracted,
                message
            )
            if save_results.get("atomic_saved"):
                logger.info(f"✅ [Ack] Memory stored atomically for user: {user_id}")
                logger.info(f"✅ [Step] Memory acknowledgement: APPROVED (all stores succeeded)")
            else:
                logger.warning(f"⚠️ [Ack] Memory NOT stored atomically for user: {user_id}")
                logger.warning(f"❌ [Step] Memory acknowledgement: DENIED (atomic save failed)")
                logger.warning(f"❌ [Step] Save results: MongoDB={save_results.get('mongodb')}, Neo4j={save_results.get('neo4j')}, Vector={save_results.get('vector')}")
        else:
            logger.debug(f"ℹ️ No extractable details found in message")
            logger.info(f"✅ [Step] No extraction needed - no details found")
            
    except Exception as e:
        logger.error(f"❌ Error in background extraction: {e}")
