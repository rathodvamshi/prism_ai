import json
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, Literal, List
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser
import pytz

# IST Timezone (Asia/Kolkata) - All date/time calculations use this
IST = ZoneInfo("Asia/Kolkata")
IST_PYTZ = pytz.timezone('Asia/Kolkata')

# ☁️ Fix timezone warning: Provide timezone mapping for dateutil parser
# This prevents "tzname IST identified but not understood" warning
TZINFOS = {
    'IST': IST_PYTZ,
    'IST (India Standard Time)': IST_PYTZ,
    'Asia/Kolkata': IST_PYTZ,
}

from app.db.mongo_client import tasks_collection
from app.utils.llm_client import get_llm_response
from app.db.redis_client import redis_client
from app.services.user_service import get_user_profile
from app.services.email_queue_service import schedule_task_reminder, remove_scheduled_email
import json as _json


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
                        "timestamp": int(datetime.now(IST).timestamp() * 1000),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
# #endregion

try:  # Optional natural language parsing
    import dateparser  # type: ignore
except Exception:  # pragma: no cover
    dateparser = None


def _has_explicit_time(text: str) -> bool:
    """Check if a time-of-day is explicitly provided."""
    time_re = re.compile(r"\b\d{1,2}(:\d{2})?\s*(am|pm)?\b", re.IGNORECASE)
    parts = ["morning", "evening", "afternoon", "tonight", "midnight", "noon"]
    return bool(time_re.search(text)) or any(p in text.lower() for p in parts)


def _apply_coarse_time_bucket(text: str, base: datetime) -> datetime:
    """Assign a sensible default time bucket when user says 'evening', etc."""
    lower = text.lower()
    if "evening" in lower:
        return base.replace(hour=18, minute=0, second=0, microsecond=0)
    if "tonight" in lower or "night" in lower:
        return base.replace(hour=21, minute=0, second=0, microsecond=0)
    if "afternoon" in lower:
        return base.replace(hour=14, minute=0, second=0, microsecond=0)
    if "morning" in lower:
        return base.replace(hour=9, minute=0, second=0, microsecond=0)
    if "noon" in lower:
        return base.replace(hour=12, minute=0, second=0, microsecond=0)
    return base


def _parse_relative(text: str, now: datetime) -> Optional[datetime]:
    """Handle quick relative expressions like 'in 20 minutes'."""
    lower = text.lower()
    match = re.search(r"in\s+(\d+)\s+(minute|minutes|hour|hours)", lower)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        delta = timedelta(minutes=value) if "min" in unit else timedelta(hours=value)
        return now + delta
    return None


def _parse_next_weekday(text: str, now: datetime) -> Optional[datetime]:
    """Parse 'next friday' etc. without guessing time."""
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    lower = text.lower()
    for idx, name in enumerate(weekdays):
        if f"next {name}" in lower:
            target = idx
            current = now.weekday()
            days_ahead = (target - current + 7) % 7
            days_ahead = days_ahead if days_ahead else 7
            return now + timedelta(days=days_ahead)
    return None


def normalize_due_date(raw: Optional[str], fallback_text: str, now: Optional[datetime] = None) -> Tuple[Optional[datetime], Optional[str]]:
    """
    Convert human time language to a concrete datetime in IST (Asia/Kolkata).
    - Avoid guessing when time is missing (returns None to trigger clarification).
    - Supports relative phrases (in 20 minutes), coarse buckets (evening), next weekday, and standard parsing.
    - ALL calculations are done in IST timezone.
    """
    now = now or datetime.now(IST)
    if not (raw or fallback_text):
        _agent_log("H1", "task_service.py:normalize_due_date", "no input", {"raw": raw, "fallback": fallback_text})
        return None, None

    # Always check RELATIVE expressions on the full user message first,
    # then on the model's field. This guarantees "in 10 min" is computed
    # from current server time and never guessed by the model.
    combined_for_relative = f"{fallback_text or ''} {raw or ''}"
    _agent_log("H1", "task_service.py:normalize_due_date", "start", {"raw": raw, "fallback": fallback_text, "combined": combined_for_relative, "now": now.isoformat()})

    # 1) Relative phrases (in 10 minutes, in 2 hours, etc.)
    rel = _parse_relative(combined_for_relative, now)
    if rel:
        _agent_log("H1", "task_service.py:normalize_due_date", "relative_match", {"value": rel.isoformat()})
        return rel, rel.strftime("%A, %b %d, %Y at %I:%M %p (IST)")

    # 2) Next weekday (next Friday, etc.)
    nxt = _parse_next_weekday(combined_for_relative, now)
    if nxt and _has_explicit_time(combined_for_relative):
        nxt = _apply_coarse_time_bucket(combined_for_relative, nxt)
        _agent_log("H1", "task_service.py:normalize_due_date", "weekday_match", {"value": nxt.isoformat()})
        return nxt, nxt.strftime("%A, %b %d, %Y at %I:%M %p (IST)")
    elif nxt and not _has_explicit_time(combined_for_relative):
        _agent_log("H1", "task_service.py:normalize_due_date", "weekday_no_time", {"weekday": nxt.isoformat()})
        return None, None  # Ask for time explicitly

    # 3) Coarse buckets (today evening, tonight, etc.)
    candidate_bucket = combined_for_relative.lower()
    if any(k in candidate_bucket for k in ["evening", "afternoon", "morning", "tonight", "noon"]):
        base = now
        if "tomorrow" in candidate_bucket:
            base = now + timedelta(days=1)
        bucketed = _apply_coarse_time_bucket(candidate_bucket, base)
        _agent_log("H1", "task_service.py:normalize_due_date", "bucket_match", {"value": bucketed.isoformat()})
        return bucketed, bucketed.strftime("%A, %b %d, %Y at %I:%M %p (IST)")

    # 4) Absolute dates (fallback) - prefer model field, but still use CODE to compute
    candidate_absolute = raw or fallback_text
    parsed: Optional[datetime] = None
    if dateparser:
        parsed = dateparser.parse(candidate_absolute, settings={"RELATIVE_BASE": now, "RETURN_AS_TIMEZONE_AWARE": False})
    if not parsed:
        try:
            # ☁️ Fix timezone warning: Provide tzinfos to recognize IST
            parsed = date_parser.parse(candidate_absolute, default=now, fuzzy=True, tzinfos=TZINFOS)
        except Exception:
            parsed = None

    if parsed:
        # If user said "tomorrow" without time, don't assume the current time; ask.
        if not _has_explicit_time(candidate_absolute):
            return None, None
        # Ensure parsed datetime is in IST
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=IST)
        else:
            parsed = parsed.astimezone(IST)
        if parsed < now:
            parsed = parsed + timedelta(days=1)
        _agent_log("H1", "task_service.py:normalize_due_date", "absolute_match", {"value": parsed.isoformat()})
        return parsed, parsed.strftime("%A, %b %d, %Y at %I:%M %p (IST)")

    _agent_log("H1", "task_service.py:normalize_due_date", "no_match", {"raw": raw, "fallback": fallback_text})
    return None, None


# ⚠️ MUST BE 'async def'
async def extract_task_details(message: str, previous_ai_message: Optional[str] = None, user_id: Optional[str] = None) -> dict:
    """
    Extracts structured task details from conversation.
    If time is missing or ambiguous, returns due_date=None to trigger clarification.
    
    🧠 MEMORY HARDENING - IST Standard:
    The user is ALWAYS in IST (India Standard Time - Asia/Kolkata).
    All time calculations use IST as the base timezone.
    """
    # CRITICAL: Always use IST (Asia/Kolkata) as the default timezone
    user_tz = "Asia/Kolkata"
    tzinfo = IST  # Use the global IST constant
    
    # Get current IST time for context
    now_ist = datetime.now(IST)
    current_time_local = now_ist.strftime("%Y-%m-%d %I:%M %p %Z")  # e.g., "2025-12-16 03:00 PM IST"

    # Build a compact conversation snippet for the model when we have history
    if previous_ai_message:
        combined_prompt = (
            "Previous AI message:\n"
            f"{previous_ai_message}\n\n"
            "User reply (may only contain the missing detail like time or date):\n"
            f"{message}"
        )
    else:
        combined_prompt = message

    system_prompt = f"""
    You are a task extractor for a personal assistant.
    Current Date & Time: {current_time_local}
    
    CRITICAL RULES:
    1. The user is in **IST (India Standard Time - Asia/Kolkata)**.
    2. If user says "Tomorrow at 5 PM", calculate based on Current Date in IST.
    3. Return 'due_date' as a clear string (e.g., "tomorrow at 2 PM IST").
    4. Ambiguity Check: If the user says "at 2" or "at 8" without AM/PM, set "is_ambiguous": true.
    5. Missing Time: If they say "tomorrow" without a time, set "missing_time": true.
    6. Context: Use previous AI message to understand answers like "PM" or "Tomorrow".

    Return JSON:
    {{
        "task_description": "Buy milk",
        "due_date": "tomorrow at 2 PM",
        "missing_time": false,
        "is_ambiguous": false,
        "clarification_question": null
    }}

    Example of Ambiguity:
    Input: "Remind me at 7"
    Output: {{ "task_description": "Remind me", "due_date": "7:00", "is_ambiguous": true, "clarification_question": "Did you mean 7 AM or 7 PM?" }}
    """

    response = await get_llm_response(prompt=combined_prompt, system_prompt=system_prompt)
    _agent_log("H1", "task_service.py:extract_task_details", "llm_response", {"raw_response": response[:200]})

    parsed: Dict[str, Any]
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        json_str = response[start:end]
        parsed = json.loads(json_str)
        _agent_log("H1", "task_service.py:extract_task_details", "parsed_json", {"task_description": parsed.get("task_description"), "due_date_raw": parsed.get("due_date")})
    except Exception as e:
        parsed = {"task_description": message, "due_date": None}
        _agent_log("H1", "task_service.py:extract_task_details", "parse_failed", {"error": str(e), "fallback": parsed})

    task_description = parsed.get("task_description") or parsed.get("description") or message
    raw_due = parsed.get("due_date")

    normalized_dt, human = normalize_due_date(raw_due, fallback_text=message)
    _agent_log("H1", "task_service.py:extract_task_details", "normalized_result", {"normalized_iso": normalized_dt.isoformat() if normalized_dt else None, "human": human})

    is_ambiguous = bool(parsed.get("is_ambiguous"))
    missing_time_flag = bool(parsed.get("missing_time"))
    clarification_question = parsed.get("clarification_question")

    if not missing_time_flag:
        missing_time_flag = normalized_dt is None

    if not clarification_question:
        if missing_time_flag:
            clarification_question = "I'd love to remind you! ⏰ When should I set this for?"
        elif is_ambiguous:
            clarification_question = "Just to be sure, did you mean AM (morning) or PM (evening)? 🤔"

    parsed["task_description"] = task_description
    parsed["due_date_display"] = parsed.get("due_date") or raw_due
    parsed["due_date_iso"] = normalized_dt.isoformat() if normalized_dt else None
    parsed["due_date_human_readable"] = human or raw_due
    parsed["missing_time"] = missing_time_flag
    parsed["is_ambiguous"] = is_ambiguous
    parsed["clarification_question"] = clarification_question
    return parsed


async def build_task_draft(message: str, previous_ai_message: Optional[str] = None, user_id: Optional[str] = None) -> dict:
    """
    Returns a draft payload with:
      - description
      - due_date_iso (or None if missing/ambiguous)
      - due_date_human_readable
      - missing_time (bool)
    """
    _agent_log("H3", "task_service.py:build_task_draft", "entry", {"message": message[:100], "has_previous": bool(previous_ai_message)})
    details = await extract_task_details(message, previous_ai_message=previous_ai_message, user_id=user_id)
    description = details.get("task_description") or message
    due_date_iso = details.get("due_date_iso")
    due_date_human = details.get("due_date_human_readable") or due_date_iso
    missing_time = bool(details.get("missing_time")) or not bool(due_date_iso)
    is_ambiguous = bool(details.get("is_ambiguous"))
    clarification_question = details.get("clarification_question")

    recurrence = detect_recurrence_rule(message)
    _agent_log("H2", "task_service.py:build_task_draft", "recurrence_result", {"recurrence": recurrence})

    result = {
        "description": description,
        "due_date_iso": due_date_iso,
        "due_date_display": details.get("due_date_display") or due_date_human,
        "due_date_human_readable": due_date_human,
        "missing_time": missing_time,
        "is_ambiguous": is_ambiguous,
        "clarification_question": clarification_question,
        "recurrence": recurrence,
    }
    _agent_log("H3", "task_service.py:build_task_draft", "exit", {"has_due_date": bool(due_date_iso), "missing_time": missing_time})
    return result


def detect_recurrence_rule(message: str) -> Optional[Dict[str, Any]]:
    """
    Detect simple recurrence patterns from natural language.
    Returns a rule dict or None. Examples:
      - daily / every day
      - every weekday
      - every 6 hours
      - 1st of every month / every month on the 1st
    """
    msg = (message or "").lower()
    _agent_log("H2", "task_service.py:detect_recurrence_rule", "start", {"message": msg})

    # Daily / every day
    if "every day" in msg or "daily" in msg:
        return {"type": "daily"}

    # Weekdays (Mon–Fri)
    if "every weekday" in msg or "weekdays" in msg:
        return {"type": "weekday"}

    # Interval-based: every X hours
    m = re.search(r"every\s+(\d+)\s+hour", msg)
    if m:
        hours = int(m.group(1))
        if hours > 0:
            return {"type": "interval_hours", "interval_hours": hours}

    # Monthly: "1st of every month" / "every month on the 1st"
    if "every month" in msg or "each month" in msg or "monthly" in msg:
        # crude detection of day number
        day_match = re.search(r"\b([0-2]?[0-9]|3[01])(?:st|nd|rd|th)?\b", msg)
        day_of_month = int(day_match.group(1)) if day_match else 1
        return {"type": "monthly_day", "day_of_month": day_of_month}

    return None


def _draft_key(user_id: str, session_id: str) -> str:
    return f"TASK_DRAFT:{user_id}:{session_id}"


async def get_active_task_draft(user_id: str, session_id: str) -> Optional[dict]:
    """Return the active task draft for a (user, session) if any."""
    key = _draft_key(user_id, session_id)
    raw = await redis_client.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


async def set_active_task_draft(user_id: str, session_id: str, draft: dict) -> None:
    """
    Store/overwrite the active task draft for a session.
    Only ONE draft exists per (user, session).
    """
    key = _draft_key(user_id, session_id)
    # Keep drafts for a day; they can be recreated easily.
    await redis_client.set(key, json.dumps(draft), ex=24 * 3600)


async def clear_active_task_draft(user_id: str, session_id: str) -> None:
    """Clear the active task draft after confirm/cancel."""
    key = _draft_key(user_id, session_id)
    await redis_client.delete(key)


# ⚠️ Only used after explicit user confirmation
async def create_task(user_id: str, description: str, due_date_iso: str, user_email: Optional[str] = None, user_name: Optional[str] = None):
    """
    Persist a confirmed task. Requires a concrete due_date.
    Converts IST due_date to UTC for database storage (best practice).
    """
    if not due_date_iso:
        raise ValueError("due_date is required to create a task")

    try:
        due_dt = datetime.fromisoformat(due_date_iso)
        # Ensure timezone-aware datetime
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=IST)
        # Convert to UTC for storage (best practice: store UTC, display in user timezone)
        due_dt_utc = due_dt.astimezone(ZoneInfo("UTC"))
    except Exception as e:
        raise ValueError(f"due_date must be ISO format: {e}")

    now_utc = datetime.now(ZoneInfo("UTC"))
    task_doc = {
        "userId": user_id,
        "description": description,
        "due_date": due_dt_utc.replace(tzinfo=None),  # Store as naive UTC in MongoDB
        "status": "pending",
        "email_status": "queued",
        "email_retry_count": 0,
        "email_last_error": None,
        "email_sent_at": None,
        "created_at": now_utc.replace(tzinfo=None),
        "updated_at": now_utc.replace(tzinfo=None),
        "user_email": user_email,
        "user_name": user_name,
    }

    result = await tasks_collection.insert_one(task_doc)
    task_id_str = str(result.inserted_id)

    # Schedule reminder in Redis (dual-lane producer). Best-effort; surface limit warning.
    try:
        ts = due_dt_utc.timestamp()
        await schedule_task_reminder(task_id_str, user_id, ts)
    except ValueError:
        # Limit reached: keep task, warn caller.
        return {
            "warning": "Task saved, but email limit reached.",
            "task": {**task_doc, "_id": result.inserted_id},
        }

    return {
        "message": f"✅ Task saved: {description} (Due: {due_dt})",
        "task": {**task_doc, "_id": result.inserted_id},
    }


# ---- Task listing and matching helpers for chat CRUD ----

async def list_tasks_for_chat(
    user_id: str,
    status: Optional[Literal["pending", "completed"]] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return a small list of tasks for chat responses.
    ✨ OPTIMIZED: Uses projections for faster queries.
    """
    query: Dict[str, Any] = {"userId": user_id}
    if status:
        query["status"] = status
    
    # 🚀 Part 9: Projection - only essential fields for chat
    projection = {
        "description": 1,
        "due_date": 1,
        "status": 1,
        "created_at": 1,
        "updated_at": 1,
        "_id": 1
    }
    
    sort_field = "due_date" if status == "pending" else "updated_at"
    cursor = (
        tasks_collection.find(query, projection)
        .sort(sort_field, 1 if status == "pending" else -1)
        .limit(limit)
    )
    tasks: List[Dict[str, Any]] = []
    async for t in cursor:
        tasks.append(t)
    return tasks


async def find_tasks_matching_description(
    user_id: str,
    message: str,
    status: Optional[Literal["pending", "completed"]] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Find tasks whose description roughly matches words in the user message.
    Simple regex-based matching, safe for small per-user task sets.
    ✨ OPTIMIZED: Uses projections for faster queries.
    """
    msg = (message or "").lower()
    tokens = [w for w in re.split(r"\W+", msg) if len(w) > 2]
    if not tokens:
        return []

    # Build a loose regex like ".*submit.*report.*"
    pattern = ".*" + ".*".join(tokens[:3]) + ".*"
    query: Dict[str, Any] = {
        "userId": user_id,
        "description": {"$regex": pattern, "$options": "i"},
    }
    if status:
        query["status"] = status

    # 🚀 Part 9: Projection - only essential fields
    projection = {
        "description": 1,
        "due_date": 1,
        "status": 1,
        "updated_at": 1,
        "_id": 1
    }

    cursor = tasks_collection.find(query, projection).sort("updated_at", -1).limit(limit)
    tasks: List[Dict[str, Any]] = []
    async for t in cursor:
        tasks.append(t)
    return tasks

