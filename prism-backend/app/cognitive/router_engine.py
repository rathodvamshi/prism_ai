from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.cognitive.temporal import resolve_time
from app.cognitive.context_stack import (
    get_stack,
    push_context,
    pop_context,
    peek_context,
    clear_context,
)
from app.cognitive.intent_catalog import INTENTS, IntentSpec
from app.services.task_service import find_tasks_matching_description
from app.utils.preprocess import preprocess as safe_preprocess


@dataclass
class RoutingResult:
    payload: Dict[str, Any]


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _negation_check(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ["don't", "do not", "cancel", "stop", "no "])


def _split_multi_intent(text: str) -> List[str]:
    t = (text or "").strip()
    # Basic split on conjunctions without paraphrasing
    parts = []
    separators = [" and ", " then ", " also "]
    idx = 0
    while idx < len(t):
        next_pos = min([t.find(sep, idx) for sep in separators if t.find(sep, idx) != -1] or [len(t)])
        segment = t[idx:next_pos].strip()
        if segment:
            parts.append(segment)
        idx = next_pos + (3 if next_pos < len(t) else 0)
    return parts or [t]


def _classify_intent(text: str) -> str:
    # Minimal heuristic classification aligned with catalog keys
    tl = (text or "").lower()
    if any(k in tl for k in ["remind", "schedule", "set a reminder", "task"]):
        return "task_create"
    if any(k in tl for k in ["update", "reschedule"]):
        return "task_update"
    if any(k in tl for k in ["cancel", "delete", "stop"]) and "remind" in tl:
        return "task_cancel"
    if any(k in tl for k in ["what tasks", "my tasks", "list tasks", "pending tasks", "completed tasks"]):
        return "task_list"
    if any(k in tl for k in ["what did we", "what do you remember", "recall"]):
        return "recall_memory"
    if any(k in tl for k in ["who is", "what is", "price", "news", "weather", "search", "google"]):
        return "web_search"
    if any(k in tl for k in ["compare", "best", "top", "vs", "plan "]):
        return "deep_research"
    return "casual_chat"


def _extract_entities(intent: str, pre: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    # Entity-safe: rely on raw + minimal heuristics
    ents: Dict[str, Any] = {}
    if intent == "task_create":
        # Time grounding
        tr = resolve_time(raw_text)
        ents["target_time"] = tr.target_time_iso
        ents["source_of_time"] = tr.source_of_time
        # Description fallback to working text
        ents["task_name"] = raw_text
    elif intent == "task_update":
        ents["new_value"] = raw_text
        tr = resolve_time(raw_text)
        ents["new_time_iso"] = tr.target_time_iso
        ents["source_of_time"] = tr.source_of_time
    elif intent == "task_cancel":
        ents["task_id"] = None
    elif intent == "task_list":
        ents["status"] = "pending" if "pending" in raw_text.lower() else ("completed" if "completed" in raw_text.lower() else "all")
    elif intent in ("web_search", "recall_memory", "deep_research"):
        ents["query"] = raw_text
    return ents


async def route_message(user_id: str, session_id: str, user_input: str) -> RoutingResult:
    interaction_id = f"ix_{uuid.uuid4().hex[:8]}"

    # Phase 1: Dual-text preprocess, grounding
    pre = safe_preprocess(user_input)
    raw_text = pre["raw_text"]
    working_text = pre["working_text"]
    language_hint = pre.get("language_hint")

    # Multi-intent split
    segments = _split_multi_intent(raw_text)

    # For this engine, process first segment; enqueue others
    primary_text = segments[0]
    queue_next = segments[1:] or None

    # Phase 2: Understanding
    primary_intent = _classify_intent(primary_text)
    is_correction = False
    if _negation_check(primary_text) and primary_intent == "task_create":
        primary_intent = "task_cancel"
        is_correction = True

    # Entities extraction (safe, minimal)
    entities = _extract_entities(primary_intent, pre, primary_text)

    # Targeted Memory Lookup (Lazy): fill task_id for update/cancel
    clarification: Optional[Dict[str, Any]] = None
    if primary_intent in ("task_update", "task_cancel") and not entities.get("task_id"):
        matches = await find_tasks_matching_description(user_id, primary_text, status="pending", limit=5)
        if len(matches) == 1:
            m = matches[0]
            entities["task_id"] = str(m.get("_id"))
            entities["task_name"] = m.get("description")
        elif len(matches) > 1:
            # Ask user to clarify; do not guess
            options = [
                {
                    "task_id": str(m.get("_id")),
                    "description": m.get("description"),
                }
                for m in matches
            ]
            clarification = {
                "type": "task_selection",
                "question": "I found multiple matching reminders. Which one should I act on?",
                "options": options,
            }

    # Phase 3: Logic & Memory
    spec: IntentSpec = INTENTS.get(primary_intent, IntentSpec([], [], []))

    # Required Slot Validation (lazy memory lookup omitted; ask user if missing)
    missing_slots = [s for s in spec.required_slots if not entities.get(s)]
    requires_confirmation = spec.requires_confirmation

    # Context stack operations (pause/resume)
    stack = await get_stack(user_id, session_id)
    # System/meta: handle stop
    if primary_intent == "stop":
        await clear_context(user_id, session_id)

    # Phase 4: Final Payload
    payload: Dict[str, Any] = {
        "routing_meta": {
            "timestamp": _now_iso(),
            "user_id": user_id,
            "interaction_id": interaction_id,
            "language_hint": language_hint,
        },
        "intent_packet": {
            "primary_intent": primary_intent,
            "is_correction": is_correction,
            "confidence_score": 0.92,
        },
        "entities_resolved": {
            **{k: v for k, v in entities.items() if v is not None},
            "source_of_time": entities.get("source_of_time"),
            "source_of_task": "user_raw_input",
        },
        "memory_operations": {
            "read": spec.memory_read,
            "write": spec.memory_write,
            "vector_search_performed": (primary_intent in ("deep_research", "recall_memory")),
        },
        "execution_directives": {
            "requires_confirmation": requires_confirmation,
            "queue_next": queue_next,
        },
    }
    if clarification:
        payload["clarification"] = clarification

    return RoutingResult(payload=payload)
