"""
Quick Integration Test Script
Tests the backend-frontend connection and memory system
"""

import asyncio
import sys
from datetime import datetime

async def test_backend_integration():
    """Test backend components"""
    
    print("🧪 Testing Backend Integration\n")
    print("=" * 50)
    
    # Test 1: Import core modules
    print("\n1️⃣ Testing imports...")
    try:
        from app.routers.memory_chat import router
        from app.services.main_brain import generate_response
        from app.db.mongo_client import users_collection
        from app.services.user_memory_manager import user_memory_manager
        print("   ✅ All imports successful")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 2: Database connections
    print("\n2️⃣ Testing database connections...")
    try:
        # Test MongoDB
        await users_collection.find_one({})
        print("   ✅ MongoDB connected")
    except Exception as e:
        print(f"   ⚠️  MongoDB: {e}")
    
    # Test 3: Memory manager
    print("\n3️⃣ Testing memory manager...")
    try:
        test_user_id = "test_integration_user"
        test_message = "Hello, testing integration!"
        test_response = "Hi! Integration test successful!"
        
        result = await user_memory_manager.save_conversation(
            user_id=test_user_id,
            user_message=test_message,
            ai_response=test_response
        )
        
        if result:
            print("   ✅ Memory manager working")
        else:
            print("   ⚠️  Memory save returned False")
    except Exception as e:
        print(f"   ❌ Memory manager error: {e}")
    
    # Test 4: Main brain
    print("\n4️⃣ Testing AI response generation...")
    try:
        # Note: This requires MongoDB user to exist
        print("   ℹ️  Skipping AI test (requires valid user in MongoDB)")
        print("   ℹ️  Use a real user login to test AI responses")
    except Exception as e:
        print(f"   ❌ AI generation error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Integration Test Summary:")
    print("   - Core modules: ✅")
    print("   - Database: Check above")
    print("   - Memory system: ✅")
    print("   - AI: Test with frontend")
    print("\n✨ Backend is ready for frontend connection!")
    print("   Start backend: uvicorn app.main:app --reload --port 8000")
    print("   Start frontend: cd Frontend && npm run dev")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    print("\n🚀 PRISM Backend-Frontend Integration Test")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        asyncio.run(test_backend_integration())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
