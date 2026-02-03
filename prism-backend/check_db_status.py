"""
🔌 DATABASE CONNECTION STATUS
=============================
Quick check of all cloud database connections.
"""
import asyncio

async def check_all_databases():
    print("=" * 60)
    print("   🔌 PRISM AI - DATABASE CONNECTION STATUS")
    print("=" * 60)
    print()
    
    results = {}
    
    # 1. MongoDB Atlas
    print("1️⃣  MongoDB Atlas...")
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from app.config import settings
        
        client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000
        )
        await client.admin.command('ping')
        db = client.prism_db
        users_count = await db.users.count_documents({})
        print(f"    ✅ CONNECTED (Database: prism_db, Users: {users_count})")
        results['mongodb'] = True
        client.close()  # No await needed for close
    except Exception as e:
        print(f"    ❌ FAILED: {e}")
        results['mongodb'] = False
    
    # 2. Redis Cloud
    print("2️⃣  Redis Cloud...")
    try:
        from app.db.redis_client import redis_client
        pong = await redis_client.ping()
        print(f"    ✅ CONNECTED")
        results['redis'] = True
    except Exception as e:
        print(f"    ❌ FAILED: {e}")
        results['redis'] = False
    
    # 3. Neo4j Aura
    print("3️⃣  Neo4j Aura...")
    try:
        from neo4j import AsyncGraphDatabase
        from app.config import settings
        
        driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            connection_timeout=15
        )
        await driver.verify_connectivity()
        
        async with driver.session() as session:
            result = await session.run('MATCH (n) RETURN count(n) as count')
            record = await result.single()
            nodes = record["count"]
        
        print(f"    ✅ CONNECTED (Nodes: {nodes})")
        results['neo4j'] = True
        await driver.close()
    except Exception as e:
        print(f"    ❌ FAILED: {e}")
        results['neo4j'] = False
    
    # 4. Pinecone
    print("4️⃣  Pinecone...")
    try:
        from pinecone import Pinecone
        from app.config import settings
        
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index("prism-memory")
        stats = index.describe_index_stats()
        vectors = stats.get('total_vector_count', 0)
        print(f"    ✅ CONNECTED (Index: prism-memory, Vectors: {vectors})")
        results['pinecone'] = True
    except Exception as e:
        print(f"    ❌ FAILED: {e}")
        results['pinecone'] = False
    
    # Summary
    print()
    print("=" * 60)
    print("   📊 SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, status in results.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {name.upper()}")
    
    print()
    if passed == total:
        print(f"   🎉 ALL {total} DATABASES CONNECTED!")
    else:
        print(f"   ⚠️  {passed}/{total} databases connected")
    
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    asyncio.run(check_all_databases())
