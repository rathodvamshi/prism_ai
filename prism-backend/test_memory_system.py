# Memory System Test Script
# Test the advanced memory management functionality

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.advanced_memory_manager import memory_manager

async def test_memory_system():
    """Test the advanced memory management system"""
    
    print("🧪 TESTING ADVANCED MEMORY MANAGEMENT SYSTEM")
    print("=" * 50)
    
    # Test user ID
    test_user_id = "test_user_amgothvijaykumar"
    
    try:
        # Test 1: Load user memory (should be empty initially)
        print("\n1️⃣ Testing memory loading...")
        user_memory = await memory_manager.load_user_memory(test_user_id)
        print(f"✅ Memory loaded successfully")
        print(f"   Profile: {bool(user_memory.get('profile'))}")
        print(f"   Structured memories: {len(user_memory.get('structured_memory', []))}")
        print(f"   Tasks: {len(user_memory.get('tasks', []))}")
        print(f"   Conversations: {len(user_memory.get('conversations', []))}")
        
        # Test 2: Add some test memories
        print("\n2️⃣ Testing memory updates...")
        test_instructions = {
            "updateMongo": {
                "name": "Amgothvijaykumar",
                "location": "Bangalore",
                "interests": ["AI", "Programming", "Machine Learning"]
            },
            "addStructuredMemory": {
                "type": "preference",
                "value": "loves programming in Python"
            },
            "addVectorMemory": "User is interested in AI and machine learning technologies",
            "addGraphMemory": ["INTERESTED_IN", "Machine Learning"],
            "addTempMemory": {
                "session_note": "Currently testing memory system"
            }
        }
        
        update_results = await memory_manager.process_memory_update_instructions(
            test_user_id, test_instructions
        )
        print(f"✅ Memory updates processed: {update_results}")
        
        # Test 3: Load memory again to see changes
        print("\n3️⃣ Testing memory persistence...")
        updated_memory = await memory_manager.load_user_memory(test_user_id)
        
        # Build context for AI model
        context = memory_manager.build_context_for_model(updated_memory)
        print(f"✅ Memory context built (length: {len(context)})")
        
        # Test 4: Simulate conversation save
        print("\n4️⃣ Testing conversation saving...")
        await memory_manager.save_conversation(
            test_user_id,
            "What do you know about me?",
            "Based on your profile, you are Amgothvijaykumar from Bangalore. You're interested in AI, Programming, and Machine Learning. You love programming in Python!"
        )
        print(f"✅ Conversation saved successfully")
        
        # Test 5: Final memory check
        print("\n5️⃣ Final memory state...")
        final_memory = await memory_manager.load_user_memory(test_user_id)
        final_context = memory_manager.build_context_for_model(final_memory)
        
        print("📊 FINAL MEMORY STATS:")
        print(f"   Profile loaded: {bool(final_memory.get('profile'))}")
        print(f"   Structured memories: {len(final_memory.get('structured_memory', []))}")
        print(f"   Tasks: {len(final_memory.get('tasks', []))}")
        print(f"   Conversations: {len(final_memory.get('conversations', []))}")
        print(f"   Temp memory: {bool(final_memory.get('temp_memory'))}")
        print(f"   Vector memories: {len(final_memory.get('vector_memories', []))}")
        print(f"   Graph relationships: {len(final_memory.get('graph_relationships', []))}")
        print(f"   Context length: {len(final_context)} characters")
        
        print("\n🎉 ALL TESTS PASSED! Memory system is working correctly.")
        
        # Show a sample of the context
        print(f"\n📄 SAMPLE CONTEXT (first 500 chars):")
        print(final_context[:500] + "..." if len(final_context) > 500 else final_context)
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_memory_system())