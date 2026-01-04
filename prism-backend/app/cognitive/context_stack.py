from __future__ import annotations

import json
from typing import Optional, List, Dict, Any

from app.db.redis_client import redis_client


def _key(user_id: str, session_id: str) -> str:
    return f"ctxstack:{user_id}:{session_id}"


async def get_stack(user_id: str, session_id: str) -> List[Dict[str, Any]]:
    raw = await redis_client.get(_key(user_id, session_id))
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


async def save_stack(user_id: str, session_id: str, stack: List[Dict[str, Any]]) -> None:
    await redis_client.set(_key(user_id, session_id), json.dumps(stack))


async def push_context(user_id: str, session_id: str, item: Dict[str, Any]) -> List[Dict[str, Any]]:
    stack = await get_stack(user_id, session_id)
    stack.append(item)
    await save_stack(user_id, session_id, stack)
    return stack


async def pop_context(user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    stack = await get_stack(user_id, session_id)
    if not stack:
        return None
    item = stack.pop()
    await save_stack(user_id, session_id, stack)
    return item


async def peek_context(user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    stack = await get_stack(user_id, session_id)
    return stack[-1] if stack else None


async def clear_context(user_id: str, session_id: str) -> None:
    await save_stack(user_id, session_id, [])
