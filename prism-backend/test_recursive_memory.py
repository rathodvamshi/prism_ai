import asyncio
import logging
from app.services.unified_memory_orchestrator import UnifiedMemoryOrchestrator, MemoryType
from app.db.neo4j_client import neo4j_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_recursive_memory():
    print("\n🧠 TESTING RECURSIVE MEMORY (GRAPH REASONING)")
    print("============================================")
    
    orchestrator = UnifiedMemoryOrchestrator()
    user_id = "test_user_recursive"
    
    # 1. Setup Graph Data
    print("\n[1] Setting up Graph Data...")
    if neo4j_client.is_available:
        async with neo4j_client._driver.session() as session:
            # Clear previous test data
            await session.run("MATCH (u:User {id: $user_id}) DETACH DELETE u", user_id=user_id)
            
            # Create: User -> LIKES -> Quantum Computing -> RELATED_TO -> Physics
            await session.run(
                """
                MERGE (u:User {id: $user_id})
                MERGE (qc:Entity {name: 'Quantum Computing'})
                MERGE (phy:Entity {name: 'Physics'})
                
                MERGE (u)-[:LIKES {created_at: $timestamp}]->(qc)
                MERGE (qc)-[:RELATED_TO]->(phy)
                """,
                user_id=user_id,
                timestamp="2024-01-01T00:00:00"
            )
            print("   ✅ Created graph: (User) -> [LIKES] -> (Quantum Computing) -> [RELATED_TO] -> (Physics)")

    # 2. Test Holographic Retrieval
    print("\n[2] Testing Holographic Retrieval...")
    context, logs = await orchestrator.get_holographic_context(
        user_id=user_id,
        query="What should I learn next?",
        intent="learning"
    )
    
    relationships = context.get("relationships", [])
    print(f"   Found {len(relationships)} relationships")
    
    # Verify Direct Relationship
    direct = next((r for r in relationships if r['target'] == "Quantum Computing"), None)
    if direct:
        print(f"   ✅ Found Direct: {direct['type']} -> {direct['target']}")
    else:
        print("   ❌ Direct relationship missing")

    # Verify Indirect Relationship (The "Strong" Feature)
    indirect = next((r for r in relationships if r['target'] == "Physics"), None)
    if indirect:
        print(f"   ✅ Found Indirect: {indirect['type']} -> {indirect['target']}")
        print(f"      Reasoning: {indirect.get('reasoning')}")
    else:
        print("   ❌ Indirect relationship missing (Recursive retrieval failed)")
        print("   Debug Logs:")
        for log in logs:
            print(f"      {log}")

    # 3. Clean up
    print("\n[3] Cleaning up...")
    if neo4j_client.is_available:
        async with neo4j_client._driver.session() as session:
            await session.run("MATCH (u:User {id: $user_id})-[r*0..2]-(n) DETACH DELETE u, n", user_id=user_id)
        print("   ✅ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(test_recursive_memory())
