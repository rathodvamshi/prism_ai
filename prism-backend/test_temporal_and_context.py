from datetime import datetime
import pytz

import pytest

from app.cognitive.temporal import resolve_time
from app.cognitive.context_stack import get_stack, push_context, pop_context, clear_context


def test_temporal_resolver_basic():
    ist = pytz.timezone("Asia/Kolkata")
    now = ist.localize(datetime(2025, 12, 24, 20, 10, 0))
    r = resolve_time("in 2 hours", now=now, tz="Asia/Kolkata")
    assert r.target_time_iso.startswith("2025-12-24T22:10")
    assert r.source_of_time == "temporal_resolver_engine"


@pytest.mark.asyncio
async def test_context_stack_lifo():
    user_id = "u_test"
    session_id = "s_test"
    await clear_context(user_id, session_id)
    assert await get_stack(user_id, session_id) == []
    await push_context(user_id, session_id, {"intent": "task_create"})
    await push_context(user_id, session_id, {"intent": "weather_check"})
    stack = await get_stack(user_id, session_id)
    assert [i["intent"] for i in stack] == ["task_create", "weather_check"]
    last = await pop_context(user_id, session_id)
    assert last["intent"] == "weather_check"
    stack2 = await get_stack(user_id, session_id)
    assert [i["intent"] for i in stack2] == ["task_create"]
