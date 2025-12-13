#!/usr/bin/env python3
"""
Minimal FastAPI server for authentication testing
"""

import uvicorn
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PRISM AI Backend - Auth Only",
    version="0.1.0-dev",
    description="Minimal backend for testing authentication"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "active",
        "app": "PRISM_AI",
        "version": "0.1.0-alpha"
    }

# Basic auth endpoints
@app.post("/api/auth/signup")
async def signup(user_data: dict):
    logger.info(f"Signup request received: {user_data.get('email', 'No email')}")
    return {
        "message": "User registered successfully",
        "user": {
            "email": user_data.get("email"),
            "id": "test-user-id"
        },
        "access_token": "test-jwt-token",
        "token_type": "bearer"
    }

@app.post("/api/auth/login")
async def login(credentials: dict):
    logger.info(f"Login request received: {credentials.get('email', 'No email')}")
    return {
        "message": "Login successful",
        "user": {
            "email": credentials.get("email"),
            "id": "test-user-id"
        },
        "access_token": "test-jwt-token",
        "token_type": "bearer"
    }

@app.get("/api/auth/me")
async def get_current_user():
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "name": "Test User"
    }

# Chat endpoint for testing
@app.post("/api/chat/send")
async def send_message(message_data: dict):
    user_message = message_data.get("message", "")
    logger.info(f"Chat message received: {user_message}")
    return {
        "response": f"Echo: {user_message}",
        "timestamp": "2024-01-01T00:00:00Z"
    }

if __name__ == "__main__":
    print("🚀 Starting Minimal PRISM Backend...")
    print("🔗 Server: http://127.0.0.1:8000")
    print("📚 Docs: http://127.0.0.1:8000/docs")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )