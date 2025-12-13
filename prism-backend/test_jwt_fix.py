"""
Test JWT Token Fix - Verify ObjectId is used correctly
"""

import jwt
from app.config import settings

# Test token payload
def decode_sample_token(token: str):
    """Decode a JWT token to check its payload"""
    try:
        SECRET_KEY = getattr(settings, 'JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production')
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        print("🔍 Token Payload:")
        print(f"   sub (user_id): {payload.get('sub')}")
        print(f"   email: {payload.get('email')}")
        print(f"   user_id: {payload.get('user_id')}")
        print(f"   type: {payload.get('type')}")
        
        # Check if sub is an ObjectId (24 char hex string)
        sub = payload.get('sub')
        if sub and len(sub) == 24 and all(c in '0123456789abcdef' for c in sub.lower()):
            print("   ✅ 'sub' is a valid ObjectId format")
            return True
        else:
            print(f"   ❌ 'sub' is NOT a valid ObjectId (got: {sub})")
            return False
            
    except Exception as e:
        print(f"   ❌ Error decoding token: {e}")
        return False

if __name__ == "__main__":
    print("\n🧪 JWT Token Format Test\n")
    print("=" * 50)
    print("\n📝 Instructions:")
    print("   1. Login from the frontend")
    print("   2. Copy the access_token from the response")
    print("   3. Paste it below\n")
    
    # Example of what to look for
    print("✅ CORRECT Token Payload:")
    print('   {"sub": "675a1234567890abcdef1234", "email": "user@example.com", ...}')
    print('   └─ sub is a 24-character ObjectId\n')
    
    print("❌ INCORRECT Token Payload:")
    print('   {"sub": "user@example.com", "email": "user@example.com", ...}')
    print('   └─ sub is an email (WRONG!)\n')
    
    print("=" * 50)
    print("\n🎯 After restart, the 401 error should be fixed!")
    print("   The JWT token will now contain the MongoDB ObjectId")
    print("   instead of the email address.\n")
