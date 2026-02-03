import asyncio
import aiohttp
import sys
import json

BASE_URL = "http://127.0.0.1:8000"

async def check_endpoint(session, method, path, headers=None, data=None, expected_status=200):
    url = f"{BASE_URL}{path}"
    print(f"👉 Checking {method} {path}...", end=" ")
    try:
        async with session.request(method, url, headers=headers, json=data) as response:
            status = response.status
            if status == expected_status:
                print(f"✅ {status} OK")
                return True
            else:
                print(f"❌ {status} (Expected {expected_status})")
                print(f"   Response: {await response.text()}")
                return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("🚀 STARTING API HEALTH CHECK\n")
    
    async with aiohttp.ClientSession() as session:
        # 1. Public Health Check
        await check_endpoint(session, "GET", "/health")
        
        # 2. Login (Admin) - Expect 200 + OTP requirement
        login_data = {
            "email": "rathodvamshi369@gmail.com",
            "password": "your_password_here_doesnt_matter_for_structure_check" 
            # Note: actual password verification happens, so expected status might be 401 if wrong password
            # But here we just want to see if the endpoint is reachable.
        }
        # Let's use a known wrong password to see if we get 401 (reachable) or 404 (missing)
        # Actually, let's just check public endpoints first.
        
        # 3. Check Admin Stats (Unauthenticated) -> Expect 401
        await check_endpoint(session, "GET", "/admin/stats", expected_status=401)
        
        # 4. Check Chat History (Unauthenticated) -> Expect 401
        await check_endpoint(session, "GET", "/chat/chats", expected_status=401)
        
        print("\n✅ API Structure Verification Complete.")
        print("   If you see 401s for protected routes, that is GOOD (Security is working).")
        print("   If you see 404s, that is BAD (Route missing).")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
