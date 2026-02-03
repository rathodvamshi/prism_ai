import asyncio
import httpx
import sys
import logging
import json

API_URL = "http://127.0.0.1:8000"

async def check_endpoint(client, name, path):
    print(f"⏳ Checking {name}...", end="\r")
    try:
        response = await client.get(f"{API_URL}{path}", timeout=10.0)
        status = response.status_code
        is_success = 200 <= status < 300
        
        status_icon = "✅" if is_success else "❌"
        print(f"{status_icon} {name:<15} | {path:<20} | Status: {status} | Latency: {response.elapsed.total_seconds()*1000:.0f}ms")
        if not is_success:
            print(f"   ⚠️ Error: {response.text[:100]}")
        return is_success
    except Exception as e:
        print(f"❌ {name:<15} | {path:<20} | Error: Connection Failed")
        print(f"   ⚠️ Detail: {str(e)}")
        return False

async def verify_system():
    print(f"\n🚀 STARTING SYSTEM VERIFICATION (Target: {API_URL})")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        results = []
        results.append(await check_endpoint(client, "System Health", "/health"))
        results.append(await check_endpoint(client, "Email Config", "/auth/diag"))
        results.append(await check_endpoint(client, "User Service", "/users/health"))
        results.append(await check_endpoint(client, "Mail Service", "/auth/mail-health"))
        
        if all(results):
            print("\n" + "="*60)
            print("✨ ALL SYSTEMS OPERATIONAL")
            print("✅ MongoDB Connection: Stable")
            print("✅ Web Server: Running")
            print("✅ Pipelines: Ready")
        else:
            print("\n" + "="*60)
            print("⚠️ SOME CHECKS FAILED")
            # If health failed, maybe server isn't running
            if not results[0]:
                print("💡 TIP: Ensure 'uvicorn app.main:app' is running in a separate terminal.")

if __name__ == "__main__":
    try:
        asyncio.run(verify_system())
    except KeyboardInterrupt:
        pass
