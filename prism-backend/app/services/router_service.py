"""
Router service that decides intent and prepares context/action payloads
before the LLM streaming step.
"""
from typing import Any, Dict, Optional
from datetime import datetime
import logging

from app.services.search_service import search_web

logger = logging.getLogger(__name__)
from app.services.task_service import (
    build_task_draft,
    get_active_task_draft,
    set_active_task_draft,
    list_tasks_for_chat,
    find_tasks_matching_description,
)
from app.services.email_service import send_email_notification
import json as _json

# Optional capabilities
try:  # pragma: no cover
    from app.services.research_service import deep_research  # type: ignore
except Exception:  # pragma: no cover
    deep_research = None

try:  # pragma: no cover
    from app.services.media_service import play_video  # type: ignore
except Exception:  # pragma: no cover
    play_video = None


def _truncate(text: str, limit: int = 4000) -> str:
    return text[:limit] if text and len(text) > limit else text


# #region agent log helper
def _agent_log(hypothesisId: str, location: str, message: str, data: dict):
    try:
        with open(r"c:\Users\vamsh\Source\3_1\project_ps2\prism\prism-ai-studio\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(
                _json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run-debug-1",
                        "hypothesisId": hypothesisId,
                        "location": location,
                        "message": message,
                        "data": data,
                        "timestamp": int(datetime.utcnow().timestamp() * 1000),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
# #endregion


async def decide_intent(message: str, previous_ai_message: Optional[str] = None) -> str:
    """Fast, rule-based intent detection."""
    msg = (message or "").lower()
    _agent_log("H3", "router_service.py:decide_intent", "entry", {"message": msg[:100], "has_previous": bool(previous_ai_message)})

    # 🔒 TASK MODE LOCK:
    # If the previous assistant message was asking for reminder time/date,
    # treat this follow-up as part of the same task flow even if it doesn't
    # contain task keywords (e.g. "Tomorrow at 5 pm").
    if previous_ai_message:
        prev = (previous_ai_message or "").lower()
        if any(
            phrase in prev
            for phrase in [
                "when should i remind you",
                "when would you like me to remind",
                "what time should i remind",
                "when would you like me to set the reminder",
            ]
        ):
            _agent_log("H3", "router_service.py:decide_intent", "task_mode_lock", {"reason": "previous_ai_asked_time"})
            return "task_management"

    # 1) YouTube / media playback
    if ("play" in msg or "watch" in msg) and any(
        k in msg for k in ["song", "video", "youtube", "music"]
    ):
        return "youtube_play"

    # 2) Deep research for complex buying / planning / comparison queries
    # Prefer phrase-based triggers to avoid overusing slow deep research.
    deep_triggers = [
        "find best",
        "compare",
        "review of",
        "reviews of",
        "vs",
        "versus",
        "difference between",
        "plan a",
        "plan my",
        "suggest a good",
        "recommend a good",
    ]
    if any(x in msg for x in deep_triggers):
        return "deep_research"

    # Backwards-compatible: product-style deep research (for rich shopping queries)
    if any(k in msg for k in ["best", "top", "under", "vs", "compare", "buy"]):
        if any(k in msg for k in ["laptop", "phone", "camera", "monitor", "headphones", "gpu", "tv"]):
            return "deep_research"

    # 3) TASK DETECTION (reminders, todos, scheduling)
    if any(x in msg for x in ["remind", "schedule", "task", "todo", "appointment", "calendar", "set a reminder"]):
        _agent_log("H3", "router_service.py:decide_intent", "task_management_match", {"keywords": [x for x in ["remind", "schedule", "task", "todo", "appointment", "calendar", "set a reminder"] if x in msg]})
        return "task_management"

    # 4) TASK CRUD via chat (list/update/cancel)
    if "what tasks do i have" in msg or ("my tasks" in msg and "completed" not in msg):
        _agent_log("H3", "router_service.py:decide_intent", "task_list_pending_match", {})
        return "task_list_pending"
    if "what tasks did i complete" in msg or "completed tasks" in msg:
        _agent_log("H3", "router_service.py:decide_intent", "task_list_completed_match", {})
        return "task_list_completed"
    if ("update" in msg or "reschedule" in msg) and "remind" in msg:
        _agent_log("H3", "router_service.py:decide_intent", "task_update_match", {})
        return "task_update"
    if any(k in msg for k in ["cancel", "stop", "delete"]) and "remind" in msg:
        _agent_log("H3", "router_service.py:decide_intent", "task_cancel_match", {})
        return "task_cancel"

    # 5) CONVERSATIONAL MEMORY CHECK
    # Questions about the self should go to memory, not web search.
    if "my name" in msg or "who am i" in msg:
        return "general_chat"

    # 6) WEB SEARCH DETECTION (explicit factual / current queries)
    # Quick, snippet-level search (not heavy deep research).
    search_triggers = [
        "who is",
        "what is",
        "price of",
        "news",
        "weather",
        "latest",
        "trending",
        "search",
        "google",
        "current",
        "today",
        "running",
        "now",
        "live",
        "meaning of",
    ]
    if any(x in msg for x in search_triggers):
        return "web_search"

    # 7) Email / notifications
    if any(word in msg for word in ["email", "send a mail", "send mail", "gmail", "notify", "send notification"]):
        return "email_service"

    # 7) Recall / Meta / Memory questions - MUST use memory-aware pipeline
    # Handle typos and variations
    recall_keywords = [
        "what did we discuss", "what did we talk", "what did i say", "what did i tell",
        "what do you know about me", "what do you remember", "what did you learn",
        "tell me about myself", "what are my", "what's my", "what is my",
        "remind me what", "recall", "remember when", "earlier we", "previously",
        "what we have", "what we discussed", "what we talked", "what did we",
        "which movies i", "which movies do i", "what movies i", "what movies do i",
        "what did i just tell", "what did i just say", "what i just told", "what i just said",
        "what do you remember about", "what do you know about my", "what are my preferences"
    ]
    # Check for recall patterns (handle typos like "disscuddes")
    recall_patterns = [
        "what.*discuss", "what.*talk", "what.*say", "what.*tell",
        "what.*know.*me", "what.*remember", "which.*i.*love", "what.*i.*love",
        "what.*i.*just.*tell", "what.*i.*just.*say", "what.*you.*remember.*about"
    ]
    import re
    if any(keyword in msg for keyword in recall_keywords) or \
       any(re.search(pattern, msg) for pattern in recall_patterns):
        return "recall_memory"  # Special intent for memory recall
    
    # 8) Fallback: rich, memory-enhanced general chat
    return "general_chat"


async def process_request(
    message: str,
    user_id: str,
    user_email: Optional[str] = None,
    previous_ai_message: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Decide intent and gather context/action payloads.
    Returns:
      {
        intent: str,
        context: str,
        action_payload: Any,
        direct_reply: Optional[str],
      }
    """
    intent = await decide_intent(message, previous_ai_message=previous_ai_message)
    _agent_log("H3", "router_service.py:process_request", "intent_decided", {"intent": intent, "msg": message, "prev_ai": previous_ai_message, "session_id": session_id})
    context_data: str = ""
    action_payload: Optional[Any] = None
    direct_reply: Optional[str] = None

    try:
        if intent == "youtube_play":
            if play_video is None:
                direct_reply = "Media service is unavailable right now."
            else:
                video_json = await play_video(message)
                # If nothing useful found, gracefully fall back to general chat
                if not video_json or not isinstance(video_json, dict) or not video_json.get("url"):
                    intent = "general_chat"
                    action_payload = None
                    context_data = ""
                else:
                    action_payload = {
                        "type": "youtube",
                        "payload": video_json,
                    }
                    title = video_json.get("title", "")
                    url = video_json.get("url", "")
                    context_data = (
                        "System: User wants to play a video.\n"
                        f"Title: {title}\nURL: {url}\nFull payload: {video_json}"
                    )

        elif intent == "deep_research":
            # Deep research: try rich service, fall back to simple web search or empty context
            if deep_research is not None:
                context_data = await deep_research(message)
            else:
                context_data = await search_web(message, mode="deep", max_results=5)

            # If nothing comes back, downgrade to general chat (no special tooling)
            if not context_data:
                intent = "general_chat"

        elif intent == "recall_memory":
            # Recall questions MUST use memory-aware pipeline
            # Fetch conversation history first, then merge confirmed stored memory
            # This bypasses fast path and ensures accurate recall
            logger.info(f"🧠 [Recall] Memory recall intent detected - using memory-aware pipeline")
            intent = "general_chat"  # Route through main brain for memory access
            context_data = ""  # Main brain will load memory internally
            
        elif intent == "task_management":
            # Single active draft per (user, session)
            existing_draft = None
            if session_id:
                existing_draft = await get_active_task_draft(user_id, session_id)

            # Task intent uses a human-safe confirmation loop:
            # 1) Extract description/time, 2) update or create draft, 3) only then show confirmation card.
            draft = await build_task_draft(message, previous_ai_message=previous_ai_message, user_id=user_id)

            if existing_draft:
                # Update existing draft: keep description unless user clearly changed it,
                # always override time when a new concrete time is provided.
                if not draft.get("missing_time") and not draft.get("is_ambiguous") and draft.get("due_date_iso"):
                    existing_draft["due_date_iso"] = draft["due_date_iso"]
                    existing_draft["due_date_human_readable"] = draft.get("due_date_human_readable") or draft["due_date_iso"]
                    existing_draft["due_date_display"] = draft.get("due_date_display") or draft["due_date_iso"]
                    existing_draft["missing_time"] = False
                    existing_draft["is_ambiguous"] = False
                    existing_draft["clarification_question"] = draft.get("clarification_question")
                    # If a recurrence rule is detected in the new message, update it as well
                    if draft.get("recurrence") is not None:
                        existing_draft["recurrence"] = draft["recurrence"]
                    updated = existing_draft
                else:
                    # No new time provided – stay in clarification mode
                    updated = {
                        **existing_draft,
                        "missing_time": draft.get("missing_time", existing_draft.get("missing_time", True)),
                        "is_ambiguous": draft.get("is_ambiguous", existing_draft.get("is_ambiguous", False)),
                        "clarification_question": draft.get("clarification_question") or existing_draft.get("clarification_question"),
                    }
            else:
                # First time seeing this task in this session – create a new draft
                updated = {
                    "description": draft.get("description") or message,
                    "due_date_iso": draft.get("due_date_iso"),
                    "due_date_human_readable": draft.get("due_date_human_readable"),
                    "due_date_display": draft.get("due_date_display"),
                    "missing_time": draft.get("missing_time", True),
                    "is_ambiguous": draft.get("is_ambiguous", False),
                    "clarification_question": draft.get("clarification_question"),
                    "recurrence": draft.get("recurrence"),
                }

            # Persist the updated draft so ALL further time messages update the same object
            if session_id:
                await set_active_task_draft(user_id, session_id, updated)
                _agent_log("H3", "router_service.py:process_request", "draft_saved", {"session_id": session_id, "draft_keys": list(updated.keys())})

            task_description = updated.get("description") or message
            due_date_iso = updated.get("due_date_iso")
            due_date_human = updated.get("due_date_human_readable") or due_date_iso
            is_ambiguous = updated.get("is_ambiguous", False)
            clarification_question = updated.get("clarification_question")

            # Ambiguity or missing time -> ask a question, treat as chat reply (no card)
            if updated.get("missing_time") or is_ambiguous or not due_date_iso:
                intent = "general_chat"
                context_data = ""
                action_payload = None
                direct_reply = clarification_question or (
                    "I'd love to remind you! ⏰ When should I set this for?"
                    if updated.get("missing_time")
                    else "Just to be sure, did you mean AM or PM? 🤔"
                )
            else:
                # We have description and time – show confirmation card using UPDATED draft.
                intent = "task_confirmation"
                context_data = ""
                action_payload = {
                    "type": "task_draft",
                    "payload": {
                        "description": task_description,
                        "due_date": updated.get("due_date_display") or due_date_iso,
                        "due_date_iso": due_date_iso,
                        "due_date_human_readable": due_date_human,
                        "recurrence": updated.get("recurrence"),
                    },
                }
                direct_reply = (
                    f"Got it! I've drafted a reminder for **{task_description}** at **{due_date_human}**. Does this look right?"
                )
                _agent_log("H3", "router_service.py:process_request", "confirmation_ready", {"description": task_description, "due": due_date_iso, "recurrence": updated.get("recurrence")})

        elif intent == "web_search":
            context_data = await search_web(message, mode="quick")
            if not context_data:
                intent = "general_chat"

        elif intent == "task_list_pending":
            tasks = await list_tasks_for_chat(user_id, status="pending", limit=5)
            if not tasks:
                direct_reply = "You have no pending reminders right now."
            else:
                lines = ["📋 Here are your pending tasks:"]
                for t in tasks:
                    desc = t.get("description", "Untitled task")
                    due = t.get("due_date")
                    if isinstance(due, str):
                        try:
                            due_dt = datetime.fromisoformat(due)
                        except Exception:
                            due_dt = None
                    else:
                        due_dt = due
                    pretty = (
                        due_dt.strftime("%A, %b %d at %I:%M %p") if isinstance(due_dt, datetime) else "no time set"
                    )
                    lines.append(f"- **{desc}** — {pretty}")
                direct_reply = "\n".join(lines)

        elif intent == "task_list_completed":
            tasks = await list_tasks_for_chat(user_id, status="completed", limit=5)
            if not tasks:
                direct_reply = "You haven't completed any reminders recently."
            else:
                lines = ["✅ Recently completed tasks:"]
                for t in tasks:
                    desc = t.get("description", "Untitled task")
                    done = t.get("completed_at") or t.get("updated_at")
                    if isinstance(done, str):
                        try:
                            done_dt = datetime.fromisoformat(done)
                        except Exception:
                            done_dt = None
                    else:
                        done_dt = done
                    pretty = (
                        done_dt.strftime("%A, %b %d at %I:%M %p") if isinstance(done_dt, datetime) else "sometime recently"
                    )
                    lines.append(f"- **{desc}** — {pretty}")
                direct_reply = "\n".join(lines)

        elif intent == "task_update":
            # Try to find a unique matching pending task by description
            candidates = await find_tasks_matching_description(user_id, message, status="pending", limit=5)
            if not candidates:
                # Fallback: show current pending tasks
                pending = await list_tasks_for_chat(user_id, status="pending", limit=5)
                if not pending:
                    direct_reply = "I couldn't find any pending reminders to update."
                else:
                    lines = ["I couldn't match that to a specific reminder. Here are your current pending tasks:"]
                    for t in pending:
                        desc = t.get("description", "Untitled task")
                        due = t.get("due_date")
                        if isinstance(due, str):
                            try:
                                due_dt = datetime.fromisoformat(due)
                            except Exception:
                                due_dt = None
                        else:
                            due_dt = due
                        pretty = (
                            due_dt.strftime("%A, %b %d at %I:%M %p") if isinstance(due_dt, datetime) else "no time set"
                        )
                        lines.append(f"- **{desc}** — {pretty}")
                    direct_reply = "\n".join(lines)
            elif len(candidates) > 1:
                # Ask the user to clarify which task
                lines = ["I found multiple reminders that might match. Which one would you like to update?"]
                for idx, t in enumerate(candidates, start=1):
                    desc = t.get("description", "Untitled task")
                    due = t.get("due_date")
                    if isinstance(due, str):
                        try:
                            due_dt = datetime.fromisoformat(due)
                        except Exception:
                            due_dt = None
                    else:
                        due_dt = due
                    pretty = (
                        due_dt.strftime("%A, %b %d at %I:%M %p") if isinstance(due_dt, datetime) else "no time set"
                    )
                    lines.append(f"{idx}. **{desc}** — {pretty}")
                direct_reply = "\n".join(lines)
            else:
                task = candidates[0]
                base_description = task.get("description", "this reminder")
                task_id = str(task.get("_id"))

                # Build new time from the message
                draft = await build_task_draft(message, previous_ai_message=previous_ai_message)
                # Force description from the existing task to avoid LLM drift
                draft["description"] = base_description
                # Carry over existing recurrence if user didn't specify a new one
                if not draft.get("recurrence") and task.get("recurrence"):
                    draft["recurrence"] = task.get("recurrence")

                # Attach task_id and store as active draft
                draft["task_id"] = task_id
                if session_id:
                    await set_active_task_draft(user_id, session_id, draft)

                if draft.get("missing_time") or not draft.get("due_date_iso"):
                    intent = "task_update"
                    direct_reply = (
                        f"I've found your reminder to **{base_description}**.\n\n"
                        "What time should I change it to? For example, in 10 minutes or at 3 PM."
                    )
                    action_payload = None
                else:
                    due_iso = draft["due_date_iso"]
                    try:
                        due_dt = datetime.fromisoformat(due_iso)
                        pretty = due_dt.strftime("%A, %b %d at %I:%M %p")
                    except Exception:
                        pretty = draft.get("due_date_human_readable") or due_iso
                    intent = "task_update_confirmation"
                    action_payload = {
                        "type": "task_update_draft",
                        "payload": {
                            "task_id": task_id,
                            "description": base_description,
                            "due_date": due_iso,
                            "due_date_human_readable": pretty,
                            "recurrence": draft.get("recurrence"),
                        },
                    }
                    direct_reply = (
                        f"Should I reschedule your reminder to **{base_description}** "
                        f"to **{pretty}**?\n\nPlease confirm."
                    )

        elif intent == "task_cancel":
            candidates = await find_tasks_matching_description(user_id, message, status="pending", limit=5)
            if not candidates:
                pending = await list_tasks_for_chat(user_id, status="pending", limit=5)
                if not pending:
                    direct_reply = "I couldn't find any pending reminders to cancel."
                else:
                    lines = ["I couldn't match that to a specific reminder. Here are your current pending tasks:"]
                    for t in pending:
                        desc = t.get("description", "Untitled task")
                        due = t.get("due_date")
                        if isinstance(due, str):
                            try:
                                due_dt = datetime.fromisoformat(due)
                            except Exception:
                                due_dt = None
                        else:
                            due_dt = due
                        pretty = (
                            due_dt.strftime("%A, %b %d at %I:%M %p") if isinstance(due_dt, datetime) else "no time set"
                        )
                        lines.append(f"- **{desc}** — {pretty}")
                    direct_reply = "\n".join(lines)
            elif len(candidates) > 1:
                lines = ["I found multiple reminders. Which one would you like to cancel?"]
                for idx, t in enumerate(candidates, start=1):
                    desc = t.get("description", "Untitled task")
                    due = t.get("due_date")
                    if isinstance(due, str):
                        try:
                            due_dt = datetime.fromisoformat(due)
                        except Exception:
                            due_dt = None
                    else:
                        due_dt = due
                    pretty = (
                        due_dt.strftime("%A, %b %d at %I:%M %p") if isinstance(due_dt, datetime) else "no time set"
                    )
                    lines.append(f"{idx}. **{desc}** — {pretty}")
                direct_reply = "\n".join(lines)
            else:
                task = candidates[0]
                task_id = str(task.get("_id"))
                base_description = task.get("description", "this reminder")
                # Store a cancel draft so the frontend can confirm and hit /tasks/cancel
                cancel_draft = {
                    "task_id": task_id,
                    "description": base_description,
                    "operation": "cancel",
                }
                if session_id:
                    await set_active_task_draft(user_id, session_id, cancel_draft)

                intent = "task_cancel_confirmation"
                action_payload = {
                    "type": "task_cancel_draft",
                    "payload": {
                        "task_id": task_id,
                        "description": base_description,
                    },
                }
                direct_reply = (
                    f"Are you sure you want to cancel the reminder for **{base_description}**?"
                )

        elif intent == "email_service":
            direct_reply = await send_email_notification(message)

        else:
            # general_chat: no extra context
            context_data = ""

    except Exception as exc:  # pragma: no cover
        direct_reply = f"I'm having trouble routing your request right now: {exc}"
        _agent_log("H3", "router_service.py:process_request", "exception", {"error": str(exc)})

    result = {
        "intent": intent,
        "context": _truncate(context_data) if isinstance(context_data, str) else _truncate(str(context_data)),
        "action_payload": action_payload,
        "direct_reply": direct_reply,
    }
    _agent_log("H3", "router_service.py:process_request", "return", {"intent": intent, "has_direct_reply": bool(direct_reply), "has_action_payload": bool(action_payload)})
    return result

