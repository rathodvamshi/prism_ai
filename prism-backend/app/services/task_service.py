import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any, Literal, List
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser
from dateutil.tz import tzoffset

# IST Timezone (Asia/Kolkata) - All date/time calculations use this
IST = ZoneInfo("Asia/Kolkata")
# Create IST offset timezone for dateutil parser (UTC+5:30)
IST_OFFSET = tzoffset('IST', 5*3600 + 30*60)

# ☁️ Fix timezone warning: Provide timezone mapping for dateutil parser
# This prevents "tzname IST identified but not understood" warning
TZINFOS = {
    'IST': IST_OFFSET,
    'IST (India Standard Time)': IST_OFFSET,
    'Asia/Kolkata': IST_OFFSET,
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


def calculate_datetime_from_time_info(time_info: Optional[Dict], fallback_message: str, now: datetime) -> Tuple[Optional[datetime], Optional[str]]:
    """
    🎯 NEW GOLDEN RULE: Backend calculates ALL datetime, never trust LLM datetime.
    
    Args:
        time_info: LLM-extracted time information in format:
                  {"type": "relative", "value": 2, "unit": "minutes"} OR
                  {"type": "absolute", "expression": "tomorrow at 5 PM"}
        fallback_message: Original user message for parsing fallback
        now: Current IST datetime (source of truth)
    
    Returns:
        Tuple of (calculated_datetime, human_readable_string) or (None, None) if ambiguous
    """
    if not time_info:
        # Fallback: try to parse the original message directly
        return normalize_due_date(None, fallback_message, now)
    
    time_type = time_info.get("type")
    
    if time_type == "relative":
        # 🚀 RELATIVE TIME: Perfect backend calculation
        value = time_info.get("value")
        unit = time_info.get("unit", "").lower()
        
        if not value or not unit:
            return None, None
            
        try:
            value = int(value)
        except (ValueError, TypeError):
            return None, None
            
        # Calculate exact datetime using backend time
        if unit in ["minute", "minutes", "min", "mins"]:
            result_dt = now + timedelta(minutes=value)
        elif unit in ["hour", "hours", "hr", "hrs"]:
            result_dt = now + timedelta(hours=value)
        elif unit in ["second", "seconds", "sec", "secs"]:
            result_dt = now + timedelta(seconds=value)
        elif unit in ["day", "days"]:
            result_dt = now + timedelta(days=value)
        else:
            return None, None
            
        # Format human readable string
        if value == 1:
            unit_singular = unit.rstrip('s')  # Remove plural 's'
            human = f"in {value} {unit_singular} (at {result_dt.strftime('%I:%M %p IST')})"
        else:
            human = f"in {value} {unit} (at {result_dt.strftime('%I:%M %p IST')})"
            
        return result_dt, human
        
    elif time_type == "absolute":
        # 🚀 ABSOLUTE TIME: Let backend parse expression
        expression = time_info.get("expression", "")
        return normalize_due_date(expression, fallback_message, now)
    
    # Unknown type, fallback
    return normalize_due_date(None, fallback_message, now)


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
    You are a task detail extractor. Extract ONLY the task description and time duration/pattern.

    Current Date & Time: {current_time_local}
    
    🛑 CRITICAL: DO NOT calculate absolute datetime. Only extract intent and duration.
    
    EXTRACT ONLY:
    1. Task description (what to remind)  
    2. Time pattern/duration (how long from now)
    
    FOR RELATIVE TIME (in X minutes/hours):
    - Extract: {{"type": "relative", "value": 2, "unit": "minutes"}}
    - Backend will calculate exact datetime
    
    FOR ABSOLUTE TIME (tomorrow at 5 PM):  
    - Extract: {{"type": "absolute", "expression": "tomorrow at 5 PM"}}
    - Backend will parse and calculate
    
    AMBIGUITY RULES:
    - "at 7" without AM/PM → set "is_ambiguous": true
    - "tomorrow" without time → set "missing_time": true
    
    Return JSON:
    {{
        "task_description": "call someone", 
        "time_info": {{"type": "relative", "value": 2, "unit": "minutes"}},
        "missing_time": false,
        "is_ambiguous": false,
        "clarification_question": null
    }}
    
    Examples:
    "in 2 min" → {{"type": "relative", "value": 2, "unit": "minutes"}}
    "in 1 hour" → {{"type": "relative", "value": 1, "unit": "hours"}}  
    "tomorrow 9 PM" → {{"type": "absolute", "expression": "tomorrow 9 PM"}}
    "at 7" → {{"type": "absolute", "expression": "at 7", "is_ambiguous": true}}
    """

    response = await get_llm_response(prompt=combined_prompt, system_prompt=system_prompt)
    _agent_log("H1", "task_service.py:extract_task_details", "llm_response", {"raw_response": response[:200]})

    parsed: Dict[str, Any]
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        json_str = response[start:end]
        parsed = json.loads(json_str)
        _agent_log("H1", "task_service.py:extract_task_details", "parsed_json", {"task_description": parsed.get("task_description"), "time_info": parsed.get("time_info")})
    except Exception as e:
        parsed = {"task_description": message, "time_info": None}
        _agent_log("H1", "task_service.py:extract_task_details", "parse_failed", {"error": str(e), "fallback": parsed})

    task_description = parsed.get("task_description") or parsed.get("description") or message
    time_info = parsed.get("time_info")
    
    # 🎯 NEW: Backend calculates datetime based on extracted time_info
    normalized_dt, human = calculate_datetime_from_time_info(time_info, message, now_ist)
    _agent_log("H1", "task_service.py:extract_task_details", "calculated_datetime", {"normalized_iso": normalized_dt.isoformat() if normalized_dt else None, "human": human})

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
    parsed["due_date_display"] = human or (time_info.get("expression") if time_info and time_info.get("type") == "absolute" else None)
    parsed["due_date_iso"] = normalized_dt.isoformat() if normalized_dt else None
    parsed["due_date_human_readable"] = human or (time_info.get("expression") if time_info and time_info.get("type") == "absolute" else None)
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


async def ensure_no_duplicate_task(user_id: str, description: str, due_date_utc: datetime) -> None:
    """
    Prevent duplicate tasks with same description and time (within 1-minute window).
    """
    start_window = due_date_utc - timedelta(minutes=1)
    end_window = due_date_utc + timedelta(minutes=1)
    
    existing = await tasks_collection.find_one({
        "userId": user_id,
        "description": description,
        "due_date": {"$gte": start_window, "$lte": end_window},
        "status": {"$ne": "cancelled"} # Ignore cancelled
    })
    
    if existing:
        raise ValueError(f"A similar task already exists for {description} around this time.")


async def check_daily_task_limit(user_id: str) -> Tuple[bool, int]:
    """
    🎯 CHECK DAILY TASK LIMIT
    
    Check if user has reached daily task creation limit.
    Free users: 3 tasks per day
    
    Returns: (limit_reached, tasks_created_today)
    """
    # Get start of today in IST
    now_ist = datetime.now(IST)
    start_of_day_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_day_utc = start_of_day_ist.astimezone(ZoneInfo("UTC"))
    
    # Count tasks created today
    tasks_today = await tasks_collection.count_documents({
        "userId": user_id,
        "created_at": {"$gte": start_of_day_utc.replace(tzinfo=None)},
        "status": {"$ne": "cancelled"}  # Don't count cancelled tasks
    })
    
    # Free tier limit: 3 tasks per day
    DAILY_LIMIT = 3
    limit_reached = tasks_today >= DAILY_LIMIT
    
    return limit_reached, tasks_today


# ⚠️ Only used after explicit user confirmation
async def create_task(user_id: str, description: str, due_date_iso: str, user_email: Optional[str] = None, user_name: Optional[str] = None):
    """
    Persist a confirmed task. Requires a concrete due_date.
    Converts IST due_date to UTC for database storage (best practice).
    
    🎯 FREE TIER LIMIT: 3 tasks per day (upgradeable to unlimited)
    """
    if not due_date_iso:
        raise ValueError("due_date is required to create a task")
    
    # 🔒 CHECK DAILY TASK LIMIT
    limit_reached, tasks_created_today = await check_daily_task_limit(user_id)
    if limit_reached:
        # Get user profile to check premium status (future)
        # For now, all users are free tier
        raise ValueError(
            f"daily_limit_reached|You've reached your daily limit of 3 tasks! 🎯\n\n"
            f"**Tasks created today:** {tasks_created_today}/3\n\n"
            f"**Want unlimited tasks?** Upgrade to Pro to create unlimited tasks, "
            f"get priority support, and unlock premium features! ✨"
        )

    try:
        # Handle Z suffix for UTC which fromisoformat doesn't support in older Python
        if due_date_iso.endswith("Z"):
            due_date_iso = due_date_iso[:-1] + "+00:00"
            
        due_dt = datetime.fromisoformat(due_date_iso)
        # Ensure timezone-aware datetime
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=IST)
        # Convert to UTC for storage (best practice: store UTC, display in user timezone)
        due_dt_utc = due_dt.astimezone(ZoneInfo("UTC"))
    except Exception as e:
        raise ValueError(f"due_date must be ISO format: {e}")
        
    # 🛡️ DUPLICATE CHECK
    await ensure_no_duplicate_task(user_id, description, due_dt_utc)

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

    # 🎨 Create user-friendly time display
    # Convert UTC back to IST for display
    due_dt_ist = due_dt_utc.astimezone(IST)
    time_display = due_dt_ist.strftime("%I:%M %p").lstrip("0")  # "7:31 PM" not "07:31 PM"
    
    # Calculate relative time for context
    now_ist = datetime.now(IST)
    delta = due_dt_ist - now_ist
    total_minutes = int(delta.total_seconds() / 60)
    
    if total_minutes < 60:
        relative_str = f"in {total_minutes} minute{'s' if total_minutes != 1 else ''}"
    elif total_minutes < 1440:  # Less than 24 hours
        hours = total_minutes // 60
        mins = total_minutes % 60
        if mins > 0:
            relative_str = f"in {hours}h {mins}m"
        else:
            relative_str = f"in {hours} hour{'s' if hours != 1 else ''}"
    else:
        days = total_minutes // 1440
        relative_str = f"in {days} day{'s' if days != 1 else ''}"
    
    # Beautiful confirmation message
    friendly_msg = f"✅ Reminder set! I'll remind you to **{description}** at **{time_display} IST** ({relative_str})"

    return {
        "message": friendly_msg,
        "task": {**task_doc, "_id": result.inserted_id},
    }

# 🔄 Reschedule a task
async def reschedule_task(task_id: str, new_due_date_iso: str, user_id: str) -> dict:
    """
    Reschedules an existing task.
    """
    if not new_due_date_iso:
        raise ValueError("New due date is required")
    
    try:
        # Parse new date
        if new_due_date_iso.endswith("Z"):
            new_due_date_iso = new_due_date_iso[:-1] + "+00:00"
        due_dt = datetime.fromisoformat(new_due_date_iso)
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=IST)
        due_dt_utc = due_dt.astimezone(ZoneInfo("UTC"))
    except Exception as e:
        raise ValueError(f"Invalid date format: {e}")
        
    # Update MongoDB
    result = await tasks_collection.update_one(
        {"_id": ObjectId(task_id), "userId": user_id},
        {
            "$set": {
                "due_date": due_dt_utc.replace(tzinfo=None),
                "updated_at": datetime.now(ZoneInfo("UTC")).replace(tzinfo=None),
                "email_status": "queued" # Reset email status
            }
        }
    )
    
    if result.matched_count == 0:
        raise ValueError("Task not found")
        
    # Reschedule in Redis/Celery
    await remove_scheduled_email(task_id) # Remove old schedule
    await schedule_task_reminder(task_id, user_id, due_dt_utc.timestamp()) # Add new
    
    return {"message": f"Task rescheduled to {due_dt.strftime('%Y-%m-%d %I:%M %p')}"}

# ❌ Cancel a task
async def cancel_task(task_id: str, user_id: str) -> dict:
    """
    Cancels a task.
    """
    result = await tasks_collection.update_one(
        {"_id": ObjectId(task_id), "userId": user_id},
        {
            "$set": {
                "status": "cancelled", 
                "email_status": "cancelled",
                "updated_at": datetime.now(ZoneInfo("UTC")).replace(tzinfo=None)
            }
        }
    )
    
    if result.matched_count == 0:
        raise ValueError("Task not found")
        
    await remove_scheduled_email(task_id)
    return {"message": "Task cancelled successfully"}



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
        "completed_at": 1,  # 🚀 Added context
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
        "completed_at": 1,  # 🚀 Added context
        "_id": 1
    }

    cursor = tasks_collection.find(query, projection).sort("updated_at", -1).limit(limit)
    tasks: List[Dict[str, Any]] = []
    async for t in cursor:
        tasks.append(t)
    return tasks

