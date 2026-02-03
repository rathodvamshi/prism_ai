from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import dateparser
from dateparser.search import search_dates
from zoneinfo import ZoneInfo
from datetime import timezone as dt_timezone
import re

from app.config import settings


@dataclass
class TemporalResolution:
    resolved_text: str
    target_time_iso: Optional[str]
    source_of_time: Optional[str]


def resolve_time(text: str, now: Optional[datetime] = None, tz: Optional[str] = None) -> TemporalResolution:
    """
    Resolve relative/ambiguous time expressions to ISO in configured timezone.
    Returns:
       resolved_text: The text with the time expression removed (cleaned).
       target_time_iso: The ISO string of the detected time.
       source_of_time: origin string.
    """
    tz_name = tz or settings.TIMEZONE
    try:
        tzinfo = ZoneInfo(tz_name)
    except Exception:
        tzinfo = dt_timezone.utc

    base = now or datetime.now(tzinfo)

    # dateparser settings for relative parsing
    dp_settings: Dict[str, Any] = {
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": base,
        "TIMEZONE": tz_name,
        "RETURN_AS_TIMEZONE_AWARE": True,
    }

    # Attempt to find dates in the text
    # search_dates returns list of (substring, date_obj)
    try:
        found = search_dates(text, settings=dp_settings, languages=["en"])
    except Exception:
        # Fallback for safety
        found = None
    
    if not found:
        return TemporalResolution(resolved_text=text, target_time_iso=None, source_of_time=None)

    # Pick the first one found
    match_str, dt = found[0]
    
    # Normalize to timezone-aware ISO
    if dt.tzinfo is None:
        dt = tzinfo.localize(dt)
    target_iso = dt.isoformat()

    # Create cleaned text by removing the match_str case-insensitive
    pattern = re.compile(re.escape(match_str), re.IGNORECASE)
    cleaned_text = pattern.sub("", text).strip()
    
    # Clean up extra spaces
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    return TemporalResolution(
        resolved_text=cleaned_text,
        target_time_iso=target_iso,
        source_of_time="temporal_resolver_engine"
    )
