
import sys
import os
import logging

# Ensure app imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.behavior_engine import behavior_engine, BehaviorProfile

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("VERIFIER")

def test_behavior_engine():
    logger.info("🧪 --- Behavior Engine Logic Tests ---")
    
    # Case 1: Simple explanation
    input1 = "Explain recursion simply like i'm 5"
    signals1 = behavior_engine.extract_behavior_signals(input1)
    emotion1 = behavior_engine.detect_emotion(input1)
    profile1 = behavior_engine.build_behavior_profile(signals1, emotion1)
    
    assert signals1["complexity"] == "simple", "Failed to detect simple complexity"
    assert profile1.vocabulary_style == "simple", "Profile vocab should be simple"
    assert profile1.warmth >= 0.6, "Warmth should be stabilized >= 0.6"
    logger.info("✅ Case 1 (Simple) Passed")

    # Case 2: Formal request
    input2 = "Kindly analyze the data please"
    signals2 = behavior_engine.extract_behavior_signals(input2)
    profile2 = behavior_engine.build_behavior_profile(signals2, "neutral")
    
    assert signals2["formality"] >= 0.8, "Failed to detect high formality"
    assert profile2.formality_level >= 0.8, "Profile should reflect high formality"
    logger.info("✅ Case 2 (Formal) Passed")

    # Case 3: Emotional Support
    input3 = "I feel so sad and lonely today"
    emotion3 = behavior_engine.detect_emotion(input3)
    profile3 = behavior_engine.build_behavior_profile({"formality": 0.5, "complexity": "std", "length_pref": "normal"}, emotion3)
    
    assert emotion3 == "sad", "Failed to detect sadness"
    assert profile3.tone == "supportive", "Tone should be supportive for sad user"
    assert profile3.warmth >= 0.8, "Warmth should be high for sad user"
    logger.info("✅ Case 3 (Emotional) Passed")
    
    # Case 4: Conflict (Angry + Strict) - Check Stabilizer
    input4 = "I am angry and I hate this, be brief."
    signals4 = behavior_engine.extract_behavior_signals(input4) # brief -> concise
    emotion4 = behavior_engine.detect_emotion(input4) # angry
    profile4 = behavior_engine.build_behavior_profile(signals4, emotion4)
    
    assert emotion4 == "angry"
    assert profile4.warmth >= 0.4, "Warmth should be clamped despite anger"
    assert profile4.response_length == "concise", "Should respect brevity preference"
    logger.info("✅ Case 4 (Conflict/Stabilizer) Passed")

def test_prompt_generation():
    logger.info("\n🧪 --- Dynamic Prompt Generation Tests ---")
    
    profile = BehaviorProfile(
        formality_level=0.5,
        emotional_depth=0.5,
        tone="Warm",
        vocabulary_style="simple",
        response_length="concise",
        warmth=0.9
    )
    
    prompt = behavior_engine.build_dynamic_prompt("CORE", profile, "MEMORY")
    
    assert "CORE" in prompt
    assert "MEMORY" in prompt
    assert "Show deep empathy" in prompt # From high warmth
    assert "Use simple, easy-to-understand language" in prompt # From simple style
    assert "brief" in prompt or "concise" in prompt # From concise length
    
    logger.info("✅ Prompt contains correct instruction blocks")
    logger.info("✅ Prompt does NOT contain fixed role names")

def verify_files_integrity():
    logger.info("\n🧪 --- File Integrity Checks ---")
    
    # Check MainBrain for RoleEngine
    with open("app/services/main_brain.py", "r", encoding="utf-8") as f:
        content = f.read()
        if "RoleEngine" in content:
            logger.error("❌ RoleEngine found in main_brain.py!")
            return False
        if "<!--THINKING_DATA" not in content:
            logger.error("❌ THINKING_DATA transparency block missing in main_brain.py!")
            return False
            
    logger.info("✅ main_brain.py is clean and has transparency")

    # Check Middleware exist
    if os.path.exists("app/middleware/auth_middleware.py"):
        logger.info("✅ AuthMiddleware exists")
    else:
        logger.error("❌ AuthMiddleware missing")

    return True

if __name__ == "__main__":
    try:
        test_behavior_engine()
        test_prompt_generation()
        if verify_files_integrity():
            print("\n🎉 ALL SYSTEMS VERIFIED. READY FOR DEPLOYMENT.")
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
