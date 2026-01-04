import asyncio
import os
import logging
from app.services.unified_memory_orchestrator import UnifiedMemoryOrchestrator, MemoryType
from app.db.neo4j_client import neo4j_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_unified_memory():
    print("\n🧠 TESTING UNIFIED MEMORY SYSTEM")
    print("=================================")
    
    # 1. Initialize Orchestrator
    print("\n[1] Initializing Orchestrator...")
    orchestrator = UnifiedMemoryOrchestrator()
    
    user_id = "test_user_123"
    
    # 2. Test Neo4j Storage (Relationship)
    print("\n[2] Testing Neo4j Storage (Relationship)...")
    rel_content = ("INTERESTED_IN", "Quantum Computing")
    
    result, logs = await orchestrator.store_memory(
        user_id=user_id,
        memory_content=rel_content,
        memory_type=MemoryType.RELATIONSHIP
    )
    
    if result.success:
        print("   ✅ Neo4j Write Success")
    else:
        print(f"   ❌ Neo4j Write Failed: {result.reason}")
        for log in logs:
            print(f"      Log: {log}")

    # 3. Test Holographic Retrieval
    print("\n[3] Testing Holographic Retrieval...")
    context, logs = await orchestrator.get_holographic_context(
        user_id=user_id,
        query="Tell me about quantum computers",
        intent="learning"
    )
    
    print(f"   Context Retrieved Keys: {list(context.keys())}")
    
    # Verify Neo4j Data
    relationships = context.get("relationships", [])
    found_quantum = any(r['target'] == "Quantum Computing" for r in relationships)
    
    if found_quantum:
        print("   ✅ Neo4j Retrieval Verified: Found 'Quantum Computing'")
    else:
        print("   ❌ Neo4j Retrieval Failed: 'Quantum Computing' not found")
        print("   Debug Logs:")
        for log in logs:
            print(f"      {log}")

    # 4. Clean up
    print("\n[4] Cleaning up test data...")
    if neo4j_client.is_available:
        async with neo4j_client._driver.session() as session:
            await session.run(
                "MATCH (u:User {id: $user_id})-[r]-(n) DELETE r, n",
                user_id=user_id
            )
        print("   ✅ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(test_unified_memory())
