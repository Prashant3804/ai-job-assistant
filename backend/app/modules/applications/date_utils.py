"""Date and Time Utilities for Candidate Application Pipeline.

Standardizes day boundaries to Asia/Kolkata (IST):
Start of day: 00:00:00.000000 IST -> converted to UTC
End of day:   23:59:59.999999 IST -> converted to UTC
"""

from datetime import datetime, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


def get_current_business_day_range(now_dt: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """Returns the (start_utc, end_utc) for the current calendar day in Asia/Kolkata.
    
    Start: 00:00:00.000000 IST in UTC
    End:   23:59:59.999999 IST in UTC
    """
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)
    elif now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    else:
        now_dt = now_dt.astimezone(timezone.utc)

    now_kolkata = now_dt.astimezone(KOLKATA_TZ)
    start_kolkata = now_kolkata.replace(hour=0, minute=0, second=0, microsecond=0)
    end_kolkata = now_kolkata.replace(hour=23, minute=59, second=59, microsecond=999999)

    return start_kolkata.astimezone(timezone.utc), end_kolkata.astimezone(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures a datetime is timezone-aware in UTC."""
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_ist(dt: Optional[datetime]) -> Optional[datetime]:
    """Converts any datetime to Asia/Kolkata timezone."""
    if not dt:
        return None
    utc_dt = ensure_utc(dt)
    if not utc_dt:
        return None
    return utc_dt.astimezone(KOLKATA_TZ)


def format_ist(dt: Optional[datetime], fmt: str = "%d %b %Y, %I:%M %p IST") -> str:
    """Formats a datetime into a human-readable string in Asia/Kolkata timezone."""
    if not dt:
        return "Never run"
    ist_dt = to_ist(dt)
    if not ist_dt:
        return "Never run"
    return ist_dt.strftime(fmt)
