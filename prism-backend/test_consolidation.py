import asyncio
import logging
from datetime import datetime
from bson import ObjectId
from app.services.memory_consolidation_service import consolidation_service
from app.db.mongo_client import sessions_collection, users_collection
from app.db.neo4j_client import neo4j_client

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_consolidation():
    print("\n🧠 TESTING MEMORY CONSOLIDATION")
    print("==============================")
    
    user_id_str = "659d4e2d1234567890abcdef"  # Dummy ObjectId
    user_id_oid = ObjectId(user_id_str)
    
    # 1. Setup Mongo Data (Simulate Chat)
    print("\n[1] Simulating Chat Session...")
    from app.db.mongo_client import connect_to_mongo
    await connect_to_mongo()
    
    # Create user if needed
    await users_collection.update_one(
        {"_id": user_id_oid},
        {"$set": {"email": "test_consolidation@example.com", "name": "Test User"}},
        upsert=True
    )
    
    # Create session with specific patterns
    session_data = {
        "sessionId": "sess_test_123",
        "userId": user_id_oid,
        "updatedAt": datetime.utcnow(),
        "messages": [
            {"role": "user", "text": "Hello AI"},
            {"role": "assistant", "text": "Hi there!"},
            {"role": "user", "text": "I am learning Rust programming"},
            {"role": "assistant", "text": "Rust is great!"},
            {"role": "user", "text": "I live in San Francisco"},
        ]
    }
    
    await sessions_collection.update_one(
        {"sessionId": "sess_test_123"},
        {"$set": session_data},
        upsert=True
    )
    print("   ✅ Created dummy session in MongoDB")

    # 2. Run Consolidation
    print("\n[2] Running Consolidation Service...")
    result = await consolidation_service.consolidate_user_memory(user_id_str)
    
    print(f"   Result: {result}")
    
    if result["facts_committed"] >= 2:
        print("   ✅ Consolidation Success: Extracted and committed facts")
    else:
        print("   ❌ Consolidation Failed: Did not extract expected facts")

    # 3. Verify Neo4j Data
    print("\n[3] Verifying Neo4j Graph...")
    if neo4j_client.is_available:
        async with neo4j_client._driver.session() as session:
            result = await session.run(
                """
                MATCH (u:User {id: $user_id})-[r]->(n)
                RETURN type(r) as rel, n.name as target
                """,
                user_id=user_id_str
            )
            records = await result.data()
            
            found_rust = False
            found_sf = False
            
            for rec in records:
                print(f"   Found: {rec['rel']} -> {rec['target']}")
                if rec['rel'] == "LEARNING" and "Rust" in rec['target']:
                    found_rust = True
                if rec['rel'] == "LIVES_IN" and "San Francisco" in rec['target']:
                    found_sf = True
            
            if found_rust and found_sf:
                print("   ✅ Neo4j Verification Passed")
            else:
                print("   ❌ Neo4j Verification Failed")

    # 4. Clean up
    print("\n[4] Cleaning up...")
    await sessions_collection.delete_one({"sessionId": "sess_test_123"})
    await users_collection.delete_one({"_id": user_id_oid})
    if neo4j_client.is_available:
        async with neo4j_client._driver.session() as session:
            await session.run("MATCH (u:User {id: $user_id}) DETACH DELETE u", user_id=user_id_str)
    print("   ✅ Cleanup complete")

if __name__ == "__main__":
    asyncio.run(test_consolidation())
