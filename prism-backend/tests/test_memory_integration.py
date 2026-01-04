import requests
import json

BASE_URL = "http://127.0.0.1:8000"
# Use the debug user from previous sessions
USER_EMAIL = "debug_test_01@example.com"
TOKEN = "mock_token" # We might need a real token if auth is enforced, but let's try without first or use a known one if available.
# Actually, the endpoints use `get_verified_user`. I need to simulate a login or use a bypass.
# For now, let's assume I can use the existing session or a test token.
# Wait, I can use the `test_endpoint` to check if the router is up.

def test_router_health():
    print("Testing Router Health...")
    try:
        res = requests.get(f"{BASE_URL}/chat/test")
        print(f"Status: {res.status_code}")
        print(res.json())
    except Exception as e:
        print(f"Failed: {e}")

def test_graph_endpoints():
    print("\nTesting Graph Endpoints (Mock Auth)...")
    # Note: This will likely fail 401 if I don't provide a valid token.
    # I will try to login first if I can, or just check if the endpoint exists (401 is better than 404).
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # 1. Get Graph
    print("1. GET /chat/memory/graph")
    res = requests.get(f"{BASE_URL}/chat/memory/graph", headers=headers)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        print(res.json())
    else:
        print(res.text)

    # 2. Add Relationship
    print("\n2. POST /chat/memory/relationship")
    payload = {
        "relationship": "LIKES",
        "target": "Coding",
        "category": "Interest"
    }
    res = requests.post(f"{BASE_URL}/chat/memory/relationship", json=payload, headers=headers)
    print(f"Status: {res.status_code}")
    print(res.text)

    # 3. Delete Relationship
    print("\n3. DELETE /chat/memory/relationship")
    payload = {
        "relationship": "LIKES",
        "target": "Coding"
    }
    # DELETE requests with body are tricky in some clients, but requests supports it.
    res = requests.delete(f"{BASE_URL}/chat/memory/relationship", json=payload, headers=headers)
    print(f"Status: {res.status_code}")
    print(res.text)

if __name__ == "__main__":
    test_router_health()
    test_graph_endpoints()
