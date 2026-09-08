"""Daily Application Execution Window Service.

Enforces the strict application submission window:
Start: 10:00:00 AM IST (Asia/Kolkata)
End:   11:59:59 AM IST (Asia/Kolkata)

Outside this window, automatic submissions are disallowed and queued as QUEUED_FOR_NEXT_WINDOW.
Continuous background discovery, matching, and preparation continue 24/7.
"""

from datetime import datetime, time, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from zoneinfo import ZoneInfo

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")

APPLICATION_WINDOW_START = time(10, 0, 0)
APPLICATION_WINDOW_END = time(11, 59, 59, 999999)

def is_application_window_open(now_dt: Optional[datetime] = None) -> bool:
    """Returns True if the current local time in Asia/Kolkata is between 10:00:00 and 11:59:59.999999.
    
    Returns False at all other times.
    """
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)
    elif now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)

    now_kolkata = now_dt.astimezone(KOLKATA_TZ)
    current_time = now_kolkata.time()

    return APPLICATION_WINDOW_START <= current_time <= APPLICATION_WINDOW_END

def get_next_application_window(now_dt: Optional[datetime] = None) -> Tuple[datetime, str]:
    """Calculates the exact next opening datetime (in UTC) and human display string in Asia/Kolkata."""
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)
    elif now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)

    now_kolkata = now_dt.astimezone(KOLKATA_TZ)
    today_start = now_kolkata.replace(hour=10, minute=0, second=0, microsecond=0)
    today_end = now_kolkata.replace(hour=11, minute=59, second=59, microsecond=999999)

    if now_kolkata < today_start:
        next_open = today_start
    elif today_start <= now_kolkata <= today_end:
        # Currently open
        next_open = today_start
    else:
        # After 12 PM -> tomorrow at 10 AM
        next_open = today_start + timedelta(days=1)

    next_utc = next_open.astimezone(timezone.utc)
    display_str = next_open.strftime("%b %d, 10:00 AM IST")
    return next_utc, display_str

def get_application_window_status(now_dt: Optional[datetime] = None) -> Dict[str, Any]:
    """Returns a structured status dictionary describing current window state."""
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)
    elif now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)

    now_kolkata = now_dt.astimezone(KOLKATA_TZ)
    is_open = is_application_window_open(now_kolkata)
    _, next_window_str = get_next_application_window(now_kolkata)

    status_label = "OPEN" if is_open else "CLOSED"
    next_display = (
        "Window OPEN until 11:59 AM IST"
        if is_open
        else f"Next window: {next_window_str}"
    )

    return {
        "is_open": is_open,
        "status": status_label,
        "window_schedule": "10:00 AM – 11:59 AM IST",
        "current_time_ist": now_kolkata.strftime("%b %d, %Y • %I:%M:%S %p IST"),
        "next_window_display": next_display,
        "timezone": "Asia/Kolkata",
    }
