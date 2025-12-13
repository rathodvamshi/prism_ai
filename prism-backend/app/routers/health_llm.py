from fastapi import APIRouter
from app.utils.llm_client import llm_health_check, test_personality

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/llm")
async def health_llm():
    return await llm_health_check()

@router.get("/test-personality")
async def test_new_personality():
    """Test the new energetic, friendly AI personality"""
    return await test_personality()