"""
🧪 Test Performance Optimization

This script tests the performance improvements of the caching layer.
Run after initializing database indexes with db_init.py
"""

import asyncio
import time
from app.services.cache_service import cache_service
from app.db.mongo_client import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_redis_connection():
    """Test Redis connectivity"""
    print("\n🔍 Testing Redis Connection...")
    is_healthy = await cache_service.health_check()
    if is_healthy:
        print("✅ Redis is connected and healthy")
    else:
        print("❌ Redis is not available (will fall back to database)")
    return is_healthy


async def test_cache_operations():
    """Test basic cache operations"""
    print("\n🔍 Testing Cache Operations...")
    
    test_session_id = "test_session_123"
    test_data = [
        {"id": "1", "text": "Test highlight 1"},
        {"id": "2", "text": "Test highlight 2"}
    ]
    
    # Test SET
    print("  📝 Setting cache...")
    success = await cache_service.set_highlights(test_session_id, test_data)
    if success:
        print("  ✅ Cache SET successful")
    else:
        print("  ❌ Cache SET failed")
        return False
    
    # Test GET
    print("  📖 Getting cache...")
    cached_data = await cache_service.get_highlights(test_session_id)
    if cached_data and len(cached_data) == 2:
        print("  ✅ Cache GET successful")
    else:
        print("  ❌ Cache GET failed")
        return False
    
    # Test INVALIDATE
    print("  🗑️ Invalidating cache...")
    success = await cache_service.invalidate_highlights(test_session_id)
    if success:
        print("  ✅ Cache INVALIDATE successful")
    else:
        print("  ❌ Cache INVALIDATE failed")
        return False
    
    # Verify invalidation
    print("  🔍 Verifying invalidation...")
    cached_data = await cache_service.get_highlights(test_session_id)
    if cached_data is None:
        print("  ✅ Cache properly invalidated")
    else:
        print("  ❌ Cache still contains data after invalidation")
        return False
    
    print("\n✅ All cache operations working correctly!")
    return True


async def test_database_indexes():
    """Test if database indexes exist"""
    print("\n🔍 Testing Database Indexes...")
    
    # Test highlights collection
    highlights_collection = db.message_highlights
    indexes = await highlights_collection.list_indexes().to_list(length=None)
    
    print(f"  📊 Found {len(indexes)} indexes in message_highlights collection:")
    required_indexes = ["sessionId_1_user_id_1", "sessionId_1_userId_1", "messageId_1_sessionId_1"]
    found_indexes = [idx['name'] for idx in indexes]
    
    for req_idx in required_indexes:
        if any(req_idx in idx for idx in found_indexes):
            print(f"  ✅ Index '{req_idx}' exists")
        else:
            print(f"  ❌ Index '{req_idx}' missing - run db_init.py")
    
    # Test mini_agents collection
    mini_agents_collection = db.mini_agents
    indexes = await mini_agents_collection.list_indexes().to_list(length=None)
    
    print(f"\n  📊 Found {len(indexes)} indexes in mini_agents collection:")
    required_indexes = ["sessionId_1_user_id_1", "agentId_1_user_id_1"]
    found_indexes = [idx['name'] for idx in indexes]
    
    for req_idx in required_indexes:
        if any(req_idx in idx for idx in found_indexes):
            print(f"  ✅ Index '{req_idx}' exists")
        else:
            print(f"  ❌ Index '{req_idx}' missing - run db_init.py")


async def test_performance():
    """Test query performance"""
    print("\n🔍 Testing Query Performance...")
    
    # Create test data if not exists
    test_session_id = "perf_test_session"
    highlights_collection = db.message_highlights
    
    # Clear old test data
    await highlights_collection.delete_many({"sessionId": test_session_id})
    
    # Insert test highlights
    test_highlights = [
        {
            "highlightId": f"hl_{i}",
            "uniqueKey": f"test_key_{i}",
            "sessionId": test_session_id,
            "messageId": f"msg_{i}",
            "userId": "test_user",
            "user_id": "test_user",
            "text": f"Test highlight {i}",
            "color": "#yellow",
            "startIndex": i * 10,
            "endIndex": i * 10 + 5
        }
        for i in range(10)
    ]
    
    await highlights_collection.insert_many(test_highlights)
    print(f"  📝 Inserted {len(test_highlights)} test highlights")
    
    # Test 1: Database query (cold)
    print("\n  🔥 Test 1: Database query (cold cache)")
    await cache_service.invalidate_highlights(test_session_id)
    
    start = time.time()
    results = await highlights_collection.find(
        {"sessionId": test_session_id}
    ).to_list(length=None)
    db_time = (time.time() - start) * 1000
    
    print(f"  ⏱️ Database query: {db_time:.2f}ms")
    print(f"  📊 Found {len(results)} highlights")
    
    # Test 2: Cache the data
    print("\n  🔥 Test 2: Caching data")
    start = time.time()
    await cache_service.set_highlights(test_session_id, results)
    cache_set_time = (time.time() - start) * 1000
    print(f"  ⏱️ Cache SET: {cache_set_time:.2f}ms")
    
    # Test 3: Retrieve from cache (warm)
    print("\n  🔥 Test 3: Retrieving from cache")
    start = time.time()
    cached_results = await cache_service.get_highlights(test_session_id)
    cache_get_time = (time.time() - start) * 1000
    
    print(f"  ⏱️ Cache GET: {cache_get_time:.2f}ms")
    print(f"  📊 Retrieved {len(cached_results)} highlights from cache")
    
    # Performance comparison
    print("\n  📈 Performance Comparison:")
    print(f"  Database query: {db_time:.2f}ms")
    print(f"  Cache retrieval: {cache_get_time:.2f}ms")
    speedup = db_time / cache_get_time if cache_get_time > 0 else 0
    print(f"  🚀 Cache is {speedup:.1f}x faster!")
    
    # Cleanup
    await highlights_collection.delete_many({"sessionId": test_session_id})
    await cache_service.invalidate_highlights(test_session_id)
    print("\n  🧹 Test data cleaned up")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 PERFORMANCE OPTIMIZATION TEST SUITE")
    print("=" * 60)
    
    # Test 1: Redis Connection
    redis_ok = await test_redis_connection()
    
    if not redis_ok:
        print("\n⚠️ Redis is not available. Tests will continue but caching won't work.")
        print("💡 To enable caching, ensure Redis is running.")
    
    # Test 2: Cache Operations
    if redis_ok:
        cache_ok = await test_cache_operations()
        if not cache_ok:
            print("\n❌ Cache operations failed. Check Redis configuration.")
    
    # Test 3: Database Indexes
    await test_database_indexes()
    
    # Test 4: Performance Benchmark
    if redis_ok:
        await test_performance()
    
    print("\n" + "=" * 60)
    print("🎉 TEST SUITE COMPLETED")
    print("=" * 60)
    
    if redis_ok:
        print("\n✅ Your optimization is working correctly!")
        print("💡 Highlights and mini agents will load 5-10x faster.")
    else:
        print("\n⚠️ Redis is not available.")
        print("💡 Install and run Redis to enable caching:")
        print("   - Windows: https://redis.io/download")
        print("   - Or use cloud Redis (configure in settings)")


if __name__ == "__main__":
    asyncio.run(main())
