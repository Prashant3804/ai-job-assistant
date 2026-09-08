import re
from datetime import datetime, timezone
from typing import List, Any, Optional

MONTH_MAP = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'september': 9, 'sept': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12
}

def parse_date_str(val: Optional[str], is_start: bool = True) -> Optional[float]:
    """Converts month/year strings or representations to float years (e.g. 2022.0 for Jan 2022)."""
    if not val or not str(val).strip():
        return None
    s = str(val).strip().lower()
    if any(p in s for p in ['present', 'current', 'now', 'today']):
        now = datetime.now(timezone.utc)
        return now.year + (now.month - 1) / 12.0

    # Match month name and year: e.g. 'Jan 2022' or 'January 2022'
    m_my = re.search(r'([a-z]+)[,\s\/-]+(\d{4})', s)
    if m_my:
        month_name = m_my.group(1)
        year = int(m_my.group(2))
        month = MONTH_MAP.get(month_name, 1 if is_start else 12)
        return year + (month - 1) / 12.0

    # Match year and month number: e.g. '2022-01' or '2022/06'
    m_ym = re.search(r'(\d{4})[,\s\/-]+(\d{1,2})', s)
    if m_ym:
        year = int(m_ym.group(1))
        month = max(1, min(12, int(m_ym.group(2))))
        return year + (month - 1) / 12.0

    # Match month number and year: e.g. '01/2022'
    m_my_num = re.search(r'(\d{1,2})[,\s\/-]+(\d{4})', s)
    if m_my_num:
        month = max(1, min(12, int(m_my_num.group(1))))
        year = int(m_my_num.group(2))
        return year + (month - 1) / 12.0

    # Match year only: '2022'
    m_y = re.search(r'\b(20[0-2][0-9]|19[7-9][0-9])\b', s)
    if m_y:
        year = int(m_y.group(1))
        month = 1 if is_start else 12
        return year + (month - 1) / 12.0

    return None

def calculate_total_experience_years(experiences: List[Any]) -> float:
    """Calculates non-overlapping union of experience intervals across work history records."""
    if not experiences:
        return 0.0

    intervals = []
    now = datetime.now(timezone.utc)
    current_float = now.year + (now.month - 1) / 12.0

    for exp in experiences:
        if isinstance(exp, dict):
            start_raw = exp.get('start_date')
            end_raw = exp.get('end_date')
            is_current = exp.get('is_current', False)
        else:
            start_raw = getattr(exp, 'start_date', None)
            end_raw = getattr(exp, 'end_date', None)
            is_current = getattr(exp, 'is_current', False)

        start_val = parse_date_str(start_raw, is_start=True)
        end_val = None
        if is_current or (end_raw and any(p in str(end_raw).lower() for p in ['present', 'current', 'now'])):
            end_val = current_float
        else:
            end_val = parse_date_str(end_raw, is_start=False)

        if start_val and end_val:
            if start_val <= end_val:
                intervals.append((start_val, end_val))
            else:
                intervals.append((end_val, start_val))
        elif start_val and not end_val:
            if is_current:
                intervals.append((start_val, current_float))
            else:
                intervals.append((start_val, start_val + 1.0))

    if not intervals:
        return 0.0

    # Merge overlapping intervals
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    total = sum(end - start for start, end in merged)
    return round(min(30.0, max(0.0, total)), 1)
