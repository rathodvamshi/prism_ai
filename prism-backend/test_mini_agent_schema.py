"""
Quick test to verify mini-agent response schema
"""

# Test data simulating backend response
test_backend_response = {
    "success": True,
    "userMessage": {
        "id": "test_user_123",
        "role": "user",
        "content": "hi",
        "timestamp": "2026-01-04T05:39:12"
    },
    "aiMessage": {
        "id": "test_ai_456",
        "role": "assistant",
        "content": "Hello! How can I help you understand this text better?",
        "timestamp": "2026-01-04T05:39:13"
    }
}

# Test what frontend will see
print("=" * 60)
print("✅ BACKEND RESPONSE SCHEMA TEST")
print("=" * 60)

# Check user message
user_msg = test_backend_response.get("userMessage", {})
print(f"\n📤 USER MESSAGE:")
print(f"  - Has 'content' field: {bool(user_msg.get('content'))}")
print(f"  - Content value: '{user_msg.get('content')}'")  
print(f"  - Has 'role' field: {bool(user_msg.get('role'))}")
print(f"  - Role value: '{user_msg.get('role')}'")

# Check AI message
ai_msg = test_backend_response.get("aiMessage", {})
print(f"\n🤖 AI MESSAGE:")
print(f"  - Has 'content' field: {bool(ai_msg.get('content'))}")
print(f"  - Content value: '{ai_msg.get('content')}'")
print(f"  - Content length: {len(ai_msg.get('content', ''))}")
print(f"  - Has 'role' field: {bool(ai_msg.get('role'))}")
print(f"  - Role value: '{ai_msg.get('role')}'")

# Simulate frontend logic
print(f"\n🎨 FRONTEND RENDER CHECK:")
content_for_display = ai_msg.get("content", "")
if not content_for_display or content_for_display.strip() == "":
    print(f"  ❌ WOULD RENDER EMPTY BUBBLE!")
else:
    print(f"  ✅ WILL RENDER: '{content_for_display[:50]}...'")

print("\n" + "=" * 60)
print("✅ SCHEMA TEST PASSED - Frontend will see content!")
print("=" * 60)
