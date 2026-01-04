from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import dateparser
import pytz

from app.config import settings


@dataclass
class TemporalResolution:
    resolved_text: str
    target_time_iso: Optional[str]
    source_of_time: Optional[str]


def resolve_time(text: str, now: Optional[datetime] = None, tz: Optional[str] = None) -> TemporalResolution:
    """
    Resolve relative/ambiguous time expressions to ISO in configured timezone.
    Returns resolved text (no paraphrasing) and ISO time if found.
    """
    tz_name = tz or settings.TIMEZONE
    tzinfo = pytz.timezone(tz_name)
    base = now or datetime.now(tzinfo)

    # dateparser settings for relative parsing
    dp_settings: Dict[str, Any] = {
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": base,
        "TIMEZONE": tz_name,
        "RETURN_AS_TIMEZONE_AWARE": True,
    }

    dt = dateparser.parse(text, settings=dp_settings, languages=["en"])
    if dt is None:
        return TemporalResolution(resolved_text=text, target_time_iso=None, source_of_time=None)

    # Normalize to timezone-aware ISO
    if dt.tzinfo is None:
        dt = tzinfo.localize(dt)
    target_iso = dt.isoformat()
    return TemporalResolution(resolved_text=text, target_time_iso=target_iso, source_of_time="temporal_resolver_engine")
