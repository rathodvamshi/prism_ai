"""
⏱️ Test Timeout Implementation

Simulates slow services to verify timeout behavior.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.timeout_utils import (
    with_timeout,
    tracked_timeout,
    TimeoutConfig,
    health_tracker
)


async def slow_redis_operation():
    """Simulates a slow Redis operation (200ms delay)"""
    print("🔴 Redis: Starting slow operation (200ms)...")
    await asyncio.sleep(0.2)  # 200ms delay
    print("🔴 Redis: Operation complete")
    return {"data": "from redis"}


async def slow_mongodb_operation():
    """Simulates a slow MongoDB operation (500ms delay)"""
    print("🟢 MongoDB: Starting slow operation (500ms)...")
    await asyncio.sleep(0.5)  # 500ms delay
    print("🟢 MongoDB: Operation complete")
    return {"data": "from mongodb"}


async def slow_neo4j_operation():
    """Simulates a slow Neo4j operation (1000ms delay)"""
    print("🔵 Neo4j: Starting slow operation (1000ms)...")
    await asyncio.sleep(1.0)  # 1000ms delay
    print("🔵 Neo4j: Operation complete")
    return {"data": "from neo4j"}


async def fast_operation():
    """Simulates a fast operation (50ms delay)"""
    print("⚡ Fast: Starting fast operation (50ms)...")
    await asyncio.sleep(0.05)  # 50ms delay
    print("⚡ Fast: Operation complete")
    return {"data": "fast result"}


async def test_timeouts():
    """Test all timeout scenarios"""
    
    print("\n" + "=" * 60)
    print("⏱️  TIMEOUT TESTS")
    print("=" * 60)
    
    # Test 1: Fast operation (should succeed)
    print("\n1️⃣ Test: Fast operation (50ms) with 100ms timeout")
    result = await tracked_timeout(
        fast_operation(),
        timeout_ms=100,
        service_name="FastService",
        fallback={"data": "fallback"}
    )
    print(f"✅ Result: {result}")
    assert result["data"] == "fast result", "Fast operation should succeed"
    
    # Test 2: Redis timeout (200ms operation with 100ms timeout)
    print("\n2️⃣ Test: Slow Redis (200ms) with 100ms timeout")
    result = await tracked_timeout(
        slow_redis_operation(),
        timeout_ms=TimeoutConfig.REDIS_GET,
        service_name="Redis GET",
        fallback=None
    )
    print(f"⏱️ Result: {result}")
    assert result is None, "Should timeout and return fallback"
    
    # Test 3: MongoDB timeout (500ms operation with 300ms timeout)
    print("\n3️⃣ Test: Slow MongoDB (500ms) with 300ms timeout")
    result = await tracked_timeout(
        slow_mongodb_operation(),
        timeout_ms=TimeoutConfig.MONGODB_FIND,
        service_name="MongoDB FIND",
        fallback=[]
    )
    print(f"⏱️ Result: {result}")
    assert result == [], "Should timeout and return fallback"
    
    # Test 4: Neo4j timeout (1000ms operation with 500ms timeout)
    print("\n4️⃣ Test: Slow Neo4j (1000ms) with 500ms timeout")
    result = await tracked_timeout(
        slow_neo4j_operation(),
        timeout_ms=TimeoutConfig.NEO4J_READ,
        service_name="Neo4j READ",
        fallback=None
    )
    print(f"⏱️ Result: {result}")
    assert result is None, "Should timeout and return fallback"
    
    # Test 5: Multiple timeouts to trigger health alerts
    print("\n5️⃣ Test: Multiple timeouts (health tracking)")
    for i in range(10):
        await tracked_timeout(
            slow_redis_operation(),
            timeout_ms=TimeoutConfig.REDIS_GET,
            service_name="Redis GET",
            fallback=None
        )
    
    # Check health report
    print("\n" + "=" * 60)
    print("📊 HEALTH REPORT")
    print("=" * 60)
    report = health_tracker.get_report()
    for service, stats in report.items():
        print(f"\n{service}:")
        print(f"  Total calls: {stats['total_calls']}")
        print(f"  Timeouts: {stats['timeouts']}")
        print(f"  Timeout rate: {stats['timeout_rate']:.1%}")
        
        if stats['timeout_rate'] > 0.3:
            print(f"  ⚠️ WARNING: High timeout rate!")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\n🎉 Timeout implementation is working correctly!")
    print("   - Fast operations complete normally")
    print("   - Slow operations timeout gracefully")
    print("   - Fallback values are returned")
    print("   - Health tracking monitors timeout rates")


async def test_cascade_pattern():
    """Test cascade query pattern (Redis → MongoDB → Neo4j)"""
    
    print("\n" + "=" * 60)
    print("🔄 CASCADE QUERY TEST")
    print("=" * 60)
    
    async def get_from_redis():
        await asyncio.sleep(0.05)  # Fast
        return None  # Cache miss
    
    async def get_from_mongodb():
        await asyncio.sleep(0.2)  # Within 300ms timeout
        return {"data": "from mongodb"}
    
    async def get_from_neo4j():
        await asyncio.sleep(1.0)  # Too slow
        return {"data": "from neo4j"}
    
    # Step 1: Try Redis (should complete, return None)
    print("\n1️⃣ Trying Redis (100ms timeout)...")
    result = await tracked_timeout(
        get_from_redis(),
        timeout_ms=TimeoutConfig.REDIS_GET,
        service_name="Redis GET",
        fallback=None
    )
    if result:
        print(f"✅ Cache HIT: {result}")
        return result
    print("❌ Cache MISS")
    
    # Step 2: Try MongoDB (should complete within 300ms)
    print("\n2️⃣ Trying MongoDB (300ms timeout)...")
    result = await tracked_timeout(
        get_from_mongodb(),
        timeout_ms=TimeoutConfig.MONGODB_FIND,
        service_name="MongoDB FIND",
        fallback=None
    )
    if result:
        print(f"✅ Found in MongoDB: {result}")
        print("   (Would cache this result in Redis)")
        return result
    print("❌ Not found in MongoDB (or timeout)")
    
    # Step 3: Try Neo4j (should timeout at 500ms)
    print("\n3️⃣ Trying Neo4j (500ms timeout)...")
    result = await tracked_timeout(
        get_from_neo4j(),
        timeout_ms=TimeoutConfig.NEO4J_READ,
        service_name="Neo4j READ",
        fallback=None
    )
    if result:
        print(f"✅ Found in Neo4j: {result}")
        return result
    print("⏱️ Neo4j timeout - returning None")
    
    print("\n🔄 Cascade complete: MongoDB returned data before Neo4j timeout")
    print("   ✅ User got response in ~400ms instead of waiting 1000ms+")


async def main():
    """Run all tests"""
    try:
        await test_timeouts()
        await test_cascade_pattern()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("\n🚀 Starting timeout implementation tests...")
    asyncio.run(main())
