
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

from app.db.redis_client import redis_client
from app.db.mongo_client import db
from bson import ObjectId
import json

@dataclass
class BehaviorProfile:
    formality_level: float  # 0.0 to 1.0 (Casual to Formal)
    emotional_depth: float  # 0.0 to 1.0 (Analytical to Empathetic)
    tone: str  # "supportive", "strict", "playful", "calm"
    vocabulary_style: str  # "simple", "technical", "poetic", "standard"
    response_length: str  # "concise", "normal", "detailed"
    warmth: float # 0.0 to 1.0

class BehaviorEngine:
    """
    1️⃣ CORE IDENTITY & BEHAVIOR ENGINE
    
    Responsibilities:
    - extract_behavior_signals(user_input)
    - detect_emotion(user_input)
    - build_behavior_profile(signals, emotion)
    - build_dynamic_prompt(core_identity, behavior_profile, memory_context)
    
    ⚠️ Roles are NOT stored, NOT named, NOT persisted.
    """

    def __init__(self):
        # 🧱 SYSTEM BASELINE (ONLY CONSTANT)
        self.baseline_traits = {
            "tone": "Warm",
            "style": "Polite", 
            "nature": "Solution-Oriented",
            "base_warmth": 0.6 # Minimum warmth
        }
        
        self.emotion_map = {
            "sad": {"depth": 0.9, "warmth": 0.9, "tone": "supportive", "style": "gentle"},
            "happy": {"depth": 0.6, "warmth": 0.8, "tone": "playful", "style": "enthusiastic"},
            "angry": {"depth": 0.3, "warmth": 0.4, "tone": "calm", "style": "patient"},
            "confused": {"depth": 0.5, "warmth": 0.7, "tone": "supportive", "style": "explanatory"},
            "curious": {"depth": 0.4, "warmth": 0.6, "tone": "engaging", "style": "detailed"},
            "neutral": {"depth": 0.5, "warmth": 0.6, "tone": "warm", "style": "standard"}
        }

    def extract_behavior_signals(self, user_input: str) -> Dict[str, Any]:
        """
        Analyzes user input for formality, length preference, and complexity.
        """
        signals = {
            "formality": 0.5,
            "complexity": "standard", 
            "length_pref": "normal"
        }
        
        lower_input = user_input.lower()
        
        # Formality detection
        formal_triggers = ["kindly", "please provide", "elaborate", "analyze", "regards", "sir", "madam"]
        casual_triggers = ["hey", "lol", "wanna", "gonna", "u there", "bro", "cool"]
        
        if any(t in lower_input for t in formal_triggers):
            signals["formality"] = 0.8
        elif any(t in lower_input for t in casual_triggers):
            signals["formality"] = 0.2
            
        # Complexity/Style detection
        if any(t in lower_input for t in ["explain like i'm 5", "eli5", "simply", "simple terms"]):
            signals["complexity"] = "simple"
        elif any(t in lower_input for t in ["technical", "code", "implementation", "specifics", "deep dive"]):
            signals["complexity"] = "technical"
            
        # Length preference
        if any(t in lower_input for t in ["brief", "short", "concise", "summary", "tl;dr"]):
            signals["length_pref"] = "concise"
        elif any(t in lower_input for t in ["detail", "long", "comprehensive", "full explanation"]):
            signals["length_pref"] = "detailed"
            
        return signals

    def detect_emotion(self, user_input: str) -> str:
        """
        Detects primary emotion from input.
        """
        lower = user_input.lower()
        
        emotions = {
            "sad": ["sad", "depressed", "lonely", "hurt", "cry", "failed", "bad day"],
            "happy": ["happy", "excited", "great", "love", "awesome", "won", "yay"],
            "angry": ["angry", "hate", "mad", "stupid", "annoying", "frustrated"],
            "confused": ["confused", "lost", "don't understand", "what?", "help"],
            "curious": ["why", "how", "tell me", "wonder", "interesting"]
        }
        
        for emotion, keywords in emotions.items():
            if any(k in lower for k in keywords):
                return emotion
                
        return "neutral"

    def build_behavior_profile(self, signals: Dict[str, Any], emotion: str) -> BehaviorProfile:
        """
        Synthesizes signals and emotion into a coherent profile.
        ⚠️ Behavior Stabilizer: Clamps values and enforces baseline warmth.
        """
        
        # Start with emotion-driven defaults
        emotion_settings = self.emotion_map.get(emotion, self.emotion_map["neutral"])
        
        # Modulate with signals
        formality = signals["formality"]
        
        # Conflict Resolution: If user is angry, increase warmth/patience regardless of formality
        if emotion == "angry":
            formality = max(formality, 0.6) # Stay respectful/professional
            
        # 3️⃣ Intent Confidence Threshold simulation (if formality is extreme, trust it)
        # Here we just blindly trust the signal extraction for now, but clamp it.
        
        # 1️⃣ Behavior Drift Guard & Stabilizer
        # Enforce baseline warmth always >= 0.3, but ideally >= 0.4 from defaults
        warmth = max(emotion_settings["warmth"], self.baseline_traits["base_warmth"])
        
        return BehaviorProfile(
            formality_level=formality,
            emotional_depth=emotion_settings["depth"],
            tone=emotion_settings["tone"],
            vocabulary_style=signals["complexity"],
            response_length=signals["length_pref"],
            warmth=warmth
        )

    async def get_interaction_anchor(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the interaction anchor (Redis Cache -> MongoDB Persistent).
        """
        try:
            key = f"interaction_anchor:{user_id}"
            
            # 1. Try Cache
            data = await redis_client.get(key)
            if data:
                return json.loads(data)
                
            # 2. Try MongoDB (Persistent source of truth)
            # Use ObjectId for query if valid, else string
            query_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
            
            user = await db.users.find_one({"_id": query_id}, {"preferences.interaction_anchor": 1})
            if user and "preferences" in user and "interaction_anchor" in user["preferences"]:
                anchor = user["preferences"]["interaction_anchor"]
                # Refill Cache (Long TTL for performance)
                await redis_client.setex(key, 86400, json.dumps(anchor)) # 24 hours
                return anchor
                
        except Exception as e:
            logger.warning(f"Failed to get interaction anchor: {e}")
        return None

    async def set_interaction_anchor(self, user_id: str, anchor_data: Dict[str, Any]):
        """
        Sets a PERMANENT interaction anchor (MongoDB + Redis Cache).
        """
        try:
            key = f"interaction_anchor:{user_id}"
            query_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
            
            # 1. Update Persistent Storage
            await db.users.update_one(
                {"_id": query_id},
                {"$set": {"preferences.interaction_anchor": anchor_data}},
                upsert=True
            )
            
            # 2. Update Cache (24 hours)
            await redis_client.setex(key, 86400, json.dumps(anchor_data))
            
        except Exception as e:
            logger.warning(f"Failed to set interaction anchor: {e}")

    async def clear_interaction_anchor(self, user_id: str):
        """
        Clears the interaction anchor from BOTH storage layers.
        """
        try:
            key = f"interaction_anchor:{user_id}"
            query_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
            
            # 1. Clear Redis
            await redis_client.delete(key)
            
            # 2. Clear MongoDB
            await db.users.update_one(
                {"_id": query_id},
                {"$unset": {"preferences.interaction_anchor": ""}}
            )
        except Exception as e:
            logger.warning(f"Failed to clear interaction anchor: {e}")

        return dynamic_prompt.strip()

    # Async wrapper for build_dynamic_prompt if we need async ops (which we do now for Mongo)
    # But wait, build_dynamic_prompt is called from main_brain which is async.
    # However, build_dynamic_prompt itself was sync. We need to make it async to call get_interaction_anchor (which is now async).
    
    async def build_dynamic_prompt_async(self, core_identity: str, behavior_profile: BehaviorProfile, memory_context: str, user_id: str = None) -> str:
        """
        Async version of prompt builder to support database lookups.
        """
        # 🔹 INTERACTION ANCHOR BLENDING
        anchor = None
        anchor_instruction = ""
        
        if user_id:
            anchor = await self.get_interaction_anchor(user_id)
            if anchor:
                # Blend anchor into instructions
                anchor_instruction = f"""
### ACTIVE INTERACTION MODE (Permanent User Preference)
You have been assigned a specific persona/mode by the user:
- **Relationship Tone**: {anchor.get('relationship_style', 'standard')}
- **My Nickname**: {anchor.get('assistant_nickname', 'Prism')}
- **User Nickname**: {anchor.get('user_nickname', 'User')}
- **Emotional Mode**: {anchor.get('emotional_mode', behavior_profile.tone)}

**CRITICAL IDENTITY RULE**: Do NOT self-identify as a generic AI or mentioning 'Prism' unless explicitly asked. 
Stay in character as '{anchor.get('assistant_nickname', 'Prism')}' and maintain the requested '{anchor.get('relationship_style')}' connection.
If the user asks "who are you", answer softly as {anchor.get('assistant_nickname', 'Prism')}, referencing this specific conversation context.
"""
                # Anchor overrides generic tone instructions if strong
                if anchor.get('relationship_style') in ['romantic', 'close_friend', 'playful']:
                     behavior_profile.tone = anchor.get('emotional_mode', behavior_profile.tone)
                     behavior_profile.warmth = max(behavior_profile.warmth, 0.8)

        # Reuse sync logic for the rest
        return self._construct_prompt_text(core_identity, behavior_profile, memory_context, anchor_instruction, anchor)

    def _construct_prompt_text(self, core_identity, behavior_profile, memory_context, anchor_instruction, anchor):
        # Translate profile processing to instructions
        tone_instruction = f"Be {behavior_profile.tone} and {self.baseline_traits['style']}."
        if behavior_profile.warmth > 0.7:
            tone_instruction += " Show deep empathy and warmth."
        elif behavior_profile.warmth < 0.4:
            tone_instruction += " Be professional and objective."
            
        style_instruction = ""
        if behavior_profile.vocabulary_style == "simple":
            style_instruction = "Use simple, easy-to-understand language. Avoid jargon."
        elif behavior_profile.vocabulary_style == "technical":
            style_instruction = "Use precise, technical terminology. Be rigorous."
            
        length_instruction = ""
        if behavior_profile.response_length == "concise":
            length_instruction = "Keep your response brief and to the point."
        elif behavior_profile.response_length == "detailed":
            length_instruction = "Provide a comprehensive, detailed explanation."

        follow_up_instr = 'After your response, optionally add a short follow-up asking if they want a simpler or deeper explanation, if appropriate.'

        dynamic_prompt = f"""
{core_identity}
{anchor_instruction}

### CURRENT BEHAVIORAL MODE (Computed Dynamically)
- **Tone**: {tone_instruction}
- **Style**: {style_instruction}
- **Depth**: Level {int(behavior_profile.emotional_depth * 10)}/10
- **Length**: {length_instruction}

### MEMORY CONTEXT
{memory_context}

### INSTRUCTIONS
1. Analyze the user's need.
2. Adapt your language to the defined style above.
3. {follow_up_instr}
4. **Emotional Alignment**: Start with a very short acknowledgement of their state if emotion is strong.
5. **Transparency**: Do not hide that you are an AI, but be the AI they need via the behavior defined above. { "However, fully embody the nickname and style defined in the Active Interaction Mode." if anchor else "" }

Remember: Sweet, Polite, Warm, Solution-Oriented is your baseline.
"""
        return dynamic_prompt.strip()

    # KEEP SYNC VERSION FOR BACKWARD COMPATIBILITY IF NEEDED (BUT REDUCE LOGIC)
    def build_dynamic_prompt(self, core_identity: str, behavior_profile: BehaviorProfile, memory_context: str, user_id: str = None) -> str:
        # Sync version can't await, so it skips the DB lookup if not careful.
        # But we must support it.
        # Actually, for the fix, we should migrate callers to build_dynamic_prompt_async
        return self._construct_prompt_text(core_identity, behavior_profile, memory_context, "", None)


# Singleton
behavior_engine = BehaviorEngine()
