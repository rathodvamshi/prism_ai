"""
Quick test to verify /chat/message endpoint is available
Run this after restarting the server
"""

import requests
import json

def test_chat_endpoint():
    """Test if the chat endpoint is accessible"""
    
    base_url = "http://127.0.0.1:8000"
    
    print("🧪 Testing Chat Endpoint Availability\n")
    print("=" * 50)
    
    # Test 1: Check if endpoint exists (will get 401 without auth, but not 404)
    print("\n1️⃣ Testing endpoint availability...")
    try:
        response = requests.post(
            f"{base_url}/chat/message",
            json={"message": "test"},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 404:
            print("   ❌ Endpoint NOT FOUND (404)")
            print("   ⚠️  Server needs to be restarted!")
            return False
        elif response.status_code == 401:
            print("   ✅ Endpoint EXISTS (got 401 - needs authentication)")
            return True
        elif response.status_code == 422:
            print("   ✅ Endpoint EXISTS (got 422 - validation error)")
            return True
        else:
            print(f"   ✅ Endpoint EXISTS (got {response.status_code})")
            return True
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to server")
        print("   ⚠️  Make sure server is running on port 8000")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Check health endpoint
    print("\n2️⃣ Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print(f"   ✅ Server is healthy: {response.json()}")
        else:
            print(f"   ⚠️  Health check returned {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
    
    print("\n" + "=" * 50)
    return True

if __name__ == "__main__":
    print("\n🚀 Chat Endpoint Test\n")
    
    result = test_chat_endpoint()
    
    if result:
        print("\n✅ SUCCESS: /chat/message endpoint is available!")
        print("\n📝 Next steps:")
        print("   1. Make sure you're logged in (have JWT token)")
        print("   2. Send a message from the frontend")
        print("   3. Check the response")
    else:
        print("\n❌ FAILED: Endpoint not available")
        print("\n🔧 To fix:")
        print("   1. Stop the uvicorn server (Ctrl+C)")
        print("   2. Restart with: uvicorn app.main:app --reload --port 8000")
        print("   3. Run this test again")
    
    print("\n" + "=" * 50)
