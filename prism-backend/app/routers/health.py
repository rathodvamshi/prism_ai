# Health Check Endpoint
# This endpoint is used by Render to verify the service is running

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Health check endpoint for deployment platforms
    Returns service status and timestamp
    """
    return {
        "status": "healthy",
        "service": "PRISM AI Backend",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "production"
    }
