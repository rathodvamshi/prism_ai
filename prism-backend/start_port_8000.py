#!/usr/bin/env python3
"""
Start the PRISM server on port 8000 with all endpoints
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Create the FastAPI app
app = FastAPI(
    title="PRISM Backend Server",
    version="1.0.0", 
    description="Complete PRISM backend with memory management"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic health endpoint
@app.get("/")
async def root():
    return {"message": "PRISM Backend is running on port 8000!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "port": 8000}

# Import and include routers
try:
    from app.routers.memory_chat import router as chat_router, users_router
    app.include_router(chat_router, tags=["Chat"])
    app.include_router(users_router, tags=["Users"])
    print("✅ All routers loaded successfully")
except Exception as e:
    print(f"❌ Router import error: {e}")
    
    # Fallback endpoints
    @app.get("/users/profile")
    async def fallback_profile(email: str):
        return {
            "email": email,
            "name": email.split("@")[0],
            "message": "Fallback profile endpoint"
        }
    
    @app.post("/chat/send") 
    async def fallback_chat():
        return {"reply": "Server is running but routers failed to load", "success": False}

if __name__ == "__main__":
    print("🚀 Starting PRISM Backend on http://localhost:8000")
    print("📋 Available endpoints:")
    print("   - GET  /health")
    print("   - GET  /users/profile?email=user@example.com")
    print("   - POST /chat/send")
    print("   - GET  /docs (API documentation)")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )