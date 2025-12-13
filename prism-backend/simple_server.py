#!/usr/bin/env python3
"""
Simple FastAPI server to test the memory system
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(backend_dir))

print(f"Backend directory: {backend_dir}")
print(f"Python path: {sys.path[0]}")

# Now try to import FastAPI and create a simple app
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PRISM Memory Test Server",
    version="1.0.0",
    description="Test server for PRISM memory management"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "PRISM Memory Test Server is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Server is operational"}

# Try to import and include the memory chat router
try:
    from app.routers.memory_chat import router as memory_router, users_router
    app.include_router(memory_router, tags=["Memory Chat"])
    app.include_router(users_router, tags=["Users"])
    print("✓ Successfully included memory_chat router")
    print("✓ Successfully included users router")
except ImportError as e:
    print(f"✗ Could not import routers: {e}")
    # Create a simple test endpoint instead
    @app.get("/api/memory/test")
    async def memory_test():
        return {"message": "Routers not available, but server is running"}

if __name__ == "__main__":
    import uvicorn
    print("Starting server on http://127.0.0.1:8000")
    print("✓ Memory system is ready for testing!")
    print("Available endpoints:")
    print("  - GET  http://127.0.0.1:8000/")
    print("  - GET  http://127.0.0.1:8000/health") 
    print("  - GET  http://127.0.0.1:8000/chat/test")
    print("  - POST http://127.0.0.1:8000/chat/send")
    print("  - POST http://127.0.0.1:8000/chat/memory-chat")
    print("  - POST http://127.0.0.1:8000/chat/memory-update/{user_id}")
    uvicorn.run(app, host="127.0.0.1", port=8000)