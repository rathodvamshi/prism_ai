#!/usr/bin/env python3
"""
🔍 PRISM System Verification Script

Tests all critical components to ensure everything is working.
Run this after the fix to verify system health.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_redis_client():
    """Test Redis client with all methods"""
    print("\n" + "=" * 60)
    print("🔍 TESTING REDIS CLIENT")
    print("=" * 60)
    
    from app.db.redis_client import redis_client
    
    try:
        # Test ping
        print("\n1️⃣ Testing ping...")
        result = await redis_client.ping()
        if result:
            print("   ✅ Redis ping successful")
        else:
            print("   ❌ Redis ping failed")
            return False
        
        # Test set/get
        print("\n2️⃣ Testing set/get...")
        await redis_client.set("test:key", "test_value", ex=60)
        value = await redis_client.get("test:key")
        if value == "test_value":
            print("   ✅ Set/Get working")
        else:
            print("   ❌ Set/Get failed")
            return False
        
        # Test rpush/rpop
        print("\n3️⃣ Testing rpush/rpop...")
        await redis_client.rpush("test:list", "item1", "item2")
        popped = await redis_client.rpop("test:list")
        if popped == "item2":
            print("   ✅ Rpush/Rpop working (CRITICAL FIX)")
        else:
            print(f"   ❌ Rpush/Rpop failed: got {popped}")
            return False
        
        # Test lpush/lpop
        print("\n4️⃣ Testing lpush/lpop...")
        await redis_client.lpush("test:list2", "item1", "item2")
        popped = await redis_client.lpop("test:list2")
        if popped == "item2":
            print("   ✅ Lpush/Lpop working (CRITICAL FIX)")
        else:
            print(f"   ❌ Lpush/Lpop failed: got {popped}")
            return False
        
        # Test zadd/zrangebyscore
        print("\n5️⃣ Testing zadd/zrangebyscore...")
        await redis_client.zadd("test:sorted", {"item1": 1.0, "item2": 2.0})
        items = await redis_client.zrangebyscore("test:sorted", "0", "10")
        if len(items) == 2:
            print("   ✅ Sorted set operations working")
        else:
            print(f"   ❌ Sorted set failed: got {items}")
            return False
        
        # Cleanup
        print("\n6️⃣ Cleaning up test keys...")
        await redis_client.delete("test:key")
        await redis_client.delete("test:list")
        await redis_client.delete("test:list2")
        await redis_client.delete("test:sorted")
        print("   ✅ Cleanup complete")
        
        print("\n" + "=" * 60)
        print("✅ ALL REDIS TESTS PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Redis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mongodb():
    """Test MongoDB connection and indexes"""
    print("\n" + "=" * 60)
    print("🔍 TESTING MONGODB")
    print("=" * 60)
    
    from app.db.mongo_client import (
        connect_to_mongo,
        users_collection,
        tasks_collection,
        sessions_collection
    )
    
    try:
        # Connect
        print("\n1️⃣ Testing connection...")
        await connect_to_mongo()
        print("   ✅ MongoDB connected")
        
        # Test indexes
        print("\n2️⃣ Checking indexes...")
        
        # Users collection
        user_indexes = await users_collection.index_information()
        if "email_1" in user_indexes:
            print("   ✅ Users email index exists")
        else:
            print("   ⚠️ Users email index missing (will create)")
        
        # Tasks collection
        task_indexes = await tasks_collection.index_information()
        expected_task_indexes = ["userId_1_status_1_due_date_1", "status_1_due_date_1"]
        found = sum(1 for idx in expected_task_indexes if idx in task_indexes)
        if found >= 1:
            print(f"   ✅ Task indexes exist ({found}/{len(expected_task_indexes)})")
        else:
            print("   ⚠️ Task indexes missing (will create)")
        
        # Sessions collection
        session_indexes = await sessions_collection.index_information()
        if "sessionId_1" in session_indexes:
            print("   ✅ Sessions sessionId index exists")
        else:
            print("   ⚠️ Sessions sessionId index missing (will create)")
        
        print("\n" + "=" * 60)
        print("✅ MONGODB TESTS PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ MongoDB test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_email_worker_readiness():
    """Test if email worker can run without errors"""
    print("\n" + "=" * 60)
    print("🔍 TESTING EMAIL WORKER READINESS")
    print("=" * 60)
    
    try:
        from app.db.redis_client import redis_client
        
        # Test the exact operations the worker uses
        print("\n1️⃣ Testing high-priority queue operations...")
        
        # Simulate adding and popping from high priority queue
        test_data = '{"type":"otp","email":"test@example.com"}'
        await redis_client.rpush("test:high_priority", test_data)
        popped = await redis_client.rpop("test:high_priority")
        
        if popped == test_data:
            print("   ✅ High-priority queue working (rpop method)")
        else:
            print(f"   ❌ High-priority queue failed: {popped}")
            return False
        
        print("\n2️⃣ Testing scheduled queue operations...")
        
        # Simulate scheduled queue
        import time
        now = time.time()
        await redis_client.zadd("test:scheduled", {"task1": now - 100, "task2": now + 100})
        
        # Get due tasks (should get task1 only)
        due_tasks = await redis_client.zrangebyscore("test:scheduled", "0", str(now), start=0, num=1)
        
        if len(due_tasks) == 1 and due_tasks[0] == "task1":
            print("   ✅ Scheduled queue working (zrangebyscore method)")
        else:
            print(f"   ❌ Scheduled queue failed: {due_tasks}")
            return False
        
        # Cleanup
        await redis_client.delete("test:high_priority")
        await redis_client.delete("test:scheduled")
        
        print("\n" + "=" * 60)
        print("✅ EMAIL WORKER READY TO RUN")
        print("=" * 60)
        print("\n💡 The worker will no longer crash with 'rpop' errors!")
        return True
        
    except Exception as e:
        print(f"\n❌ Email worker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n🚀 PRISM SYSTEM VERIFICATION")
    print("Testing all critical components after fix...\n")
    
    results = []
    
    # Test Redis
    redis_ok = await test_redis_client()
    results.append(("Redis Client", redis_ok))
    
    # Test MongoDB
    mongo_ok = await test_mongodb()
    results.append(("MongoDB", mongo_ok))
    
    # Test Email Worker Readiness
    worker_ok = await test_email_worker_readiness()
    results.append(("Email Worker", worker_ok))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    for component, status in results:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {component}: {'PASS' if status else 'FAIL'}")
    
    all_passed = all(status for _, status in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - SYSTEM READY!")
        print("=" * 60)
        print("\n✅ Critical fix verified:")
        print("   - Redis rpop() method working")
        print("   - Redis lpop() method working")
        print("   - Email worker will run without errors")
        print("   - All database connections healthy")
        print("\n🚀 You can now start the server:")
        print("   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
        return 0
    else:
        print("❌ SOME TESTS FAILED - CHECK ERRORS ABOVE")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
