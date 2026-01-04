import pytest
from datetime import datetime, timezone, timedelta

from app.cognitive.router_engine import route_message


@pytest.mark.asyncio
async def test_intent_entities_and_confirmation(monkeypatch):
    """
    Validates that the cognitive router:
    - Detects intent as task_update
    - Extracts grounded time entity (new_time_iso)
    - Requests confirmation per Intent Catalog
    - Emits clarification when multiple task matches are found
    """
    user_id = "user_test"
    session_id = "sess_test"

    # Case 1: Single match -> entities should include task_id/name and new_time_iso; requires_confirmation True
    async def fake_find_single(user_id_arg, text, status="pending", limit=5):
        return [
            {"_id": "t123", "description": "Server Logs"},
        ]

    import app.cognitive.router_engine as re_mod
    monkeypatch.setattr(re_mod, "find_tasks_matching_description", fake_find_single)

    msg = "Please update Server Logs to 2 hours from now."
    # Patch temporal resolution to ensure deterministic grounded time
    import app.cognitive.router_engine as re_mod_temporal_target
    class FakeTemporalRes:
        def __init__(self, iso):
            self.resolved_text = msg
            self.target_time_iso = iso
            self.source_of_time = "test"
    def fake_resolve_time(text, now=None, tz=None):
        iso = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        return FakeTemporalRes(iso)
    monkeypatch.setattr(re_mod_temporal_target, "resolve_time", fake_resolve_time)
    res = await route_message(user_id, session_id, msg)
    payload = res.payload

    assert payload["intent_packet"]["primary_intent"] == "task_update"
    ents = payload["entities_resolved"]
    assert ents.get("task_id") == "t123"
    assert ents.get("task_name") == "Server Logs"
    assert ents.get("new_time_iso"), "Expected grounded new_time_iso"

    # Confirmation directive should be set for task_update
    assert payload["execution_directives"]["requires_confirmation"] is True

    # Case 2: Multiple matches -> clarification options should be presented
    async def fake_find_multi(user_id_arg, text, status="pending", limit=5):
        return [
            {"_id": "t111", "description": "Server Logs - app"},
            {"_id": "t222", "description": "Server Logs - infra"},
        ]

    monkeypatch.setattr(re_mod, "find_tasks_matching_description", fake_find_multi)

    res2 = await route_message(user_id, session_id, msg)
    payload2 = res2.payload

    # Still task_update intent
    assert payload2["intent_packet"]["primary_intent"] == "task_update"
    # No single task_id resolved; clarification must exist
    assert "clarification" in payload2
    clar = payload2["clarification"]
    assert clar.get("type") == "task_selection"
    assert isinstance(clar.get("options"), list) and len(clar["options"]) == 2
