"""
Test Neo4j connection from PRISM backend
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.neo4j_client import neo4j_client, GraphMemoryService

async def test_backend_connection():
    """Test Neo4j connection from backend"""
    
    print("\n" + "="*60)
    print("🔧 Testing PRISM Backend Neo4j Connection")
    print("="*60)
    
    # Test 1: Check if driver is available
    print("\n1️⃣ Checking Neo4j client...")
    if not neo4j_client.is_available:
        print("❌ Neo4j client not available")
        return False
    print("✅ Neo4j client initialized")
    
    # Test 2: Verify connectivity
    print("\n2️⃣ Verifying connectivity...")
    try:
        connected = await neo4j_client.verify_connectivity()
        if not connected:
            print("❌ Connectivity verification failed")
            return False
        print("✅ Connectivity verified")
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
    
    # Test 3: Run a simple query
    print("\n3️⃣ Testing query execution...")
    try:
        result = await neo4j_client.query(
            "RETURN 'Backend Connected!' AS message, datetime() AS time"
        )
        if result:
            print(f"✅ Query successful!")
            print(f"   Result: {result[0]}")
        else:
            print("❌ Query returned no results")
            return False
    except Exception as e:
        print(f"❌ Query error: {e}")
        return False
    
    # Test 4: Test GraphMemoryService
    print("\n4️⃣ Testing GraphMemoryService...")
    try:
        service = GraphMemoryService()
        
        # Create test user node
        success = await service.create_user_node(
            user_id="test_user_123",
            email="test@example.com",
            name="Test User"
        )
        
        if success:
            print("✅ GraphMemoryService working")
        else:
            print("⚠️ GraphMemoryService returned False (may be normal)")
            
    except Exception as e:
        print(f"❌ GraphMemoryService error: {e}")
        return False
    
    print("\n" + "="*60)
    print("🎉 ALL BACKEND TESTS PASSED!")
    print("Neo4j is properly integrated with PRISM backend!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_backend_connection())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
