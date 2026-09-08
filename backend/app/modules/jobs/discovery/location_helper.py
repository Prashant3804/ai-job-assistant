import re
from typing import Optional

# Indian tech hubs and location indicators
INDIAN_LOCATIONS = {
    "india", "bangalore", "bengaluru", "hyderabad", "pune",
    "chennai", "mumbai", "delhi", "noida", "gurugram", "gurgaon",
    "kolkata", "ahmedabad", "kochi", "coimbatore", "indore",
    "chandigarh", "jaipur", "thiruvananthapuram", "bhubaneswar"
}

# Explicit exclusions / restricted regions
RESTRICTED_NON_INDIA_PATTERNS = [
    r"\busa?\b",
    r"\bunited states\b",
    r"\bus only\b",
    r"\bus-only\b",
    r"\busa only\b",
    r"\bus-remote\b",
    r"\bus remote\b",
    r"\bcanada\b",
    r"\bcanada only\b",
    r"\beurope\b",
    r"\beurope only\b",
    r"\bemea\b",
    r"\buk only\b",
    r"\bunited kingdom\b",
    r"\bgermany\b",
    r"\bfrance\b",
    r"\baustralia\b",
    r"\baustralia only\b",
    r"\blatam\b",
    r"\bbrazil\b",
    r"\bjapan\b",
    r"\bnetherlands\b",
    r"\bthe netherlands\b",
    r"\bireland\b",
    r"\bspain\b",
    r"\bsweden\b",
    r"\bpoland\b",
    r"\bswitzerland\b",
    r"\bsingapore\b",
    r"\bportugal\b",
    r"\bisrael\b",
    r"\bitaly\b",
    r"\bfrance\b",
    r"\bmexico\b"
]

# Global / Worldwide acceptance patterns
GLOBAL_PATTERNS = [
    r"\bworldwide\b",
    r"\banywhere\b",
    r"\bglobal\b",
    r"\bwork from anywhere\b",
    r"\bapac\b",
    r"\ball regions\b"
]

def is_location_eligible(job_location: Optional[str], candidate_location: Optional[str] = "India") -> bool:
    """Centralized location-eligibility helper.
    
    If candidate_location indicates India:
    - Accepts: India, Indian cities (Bangalore, etc.), Worldwide, Anywhere, Global remote, APAC.
    - Rejects: USA only, US only, Canada only, Europe only, UK only, etc.
    - Bare 'Remote' is accepted unless an explicit non-India restriction is present.
    """
    if not job_location or not job_location.strip():
        return True

    loc_lower = job_location.strip().lower()
    cand_lower = (candidate_location or "").strip().lower()

    # If candidate location is not India-focused, fallback to simple substring or True
    is_india_candidate = not cand_lower or any(ind in cand_lower for ind in ["india", "bangalore", "bengaluru", "hyderabad", "pune", "delhi", "mumbai"])
    if not is_india_candidate:
        return cand_lower in loc_lower or any(re.search(pat, loc_lower) for pat in GLOBAL_PATTERNS)

    # 1. Check for explicit Indian locations -> Always Accept
    for ind in INDIAN_LOCATIONS:
        if re.search(rf"\b{ind}\b", loc_lower):
            return True

    # 2. Check for explicit APAC / Asia / Worldwide global inclusion -> Accept
    if re.search(r"\bapac\b", loc_lower) or re.search(r"\basia\b", loc_lower) or re.search(r"\bworldwide\b", loc_lower) or re.search(r"\banywhere\b", loc_lower):
        return True

    # 3. Check for explicit non-India restrictions -> Reject
    for pat in RESTRICTED_NON_INDIA_PATTERNS:
        if re.search(pat, loc_lower):
            return False

    # 4. Check for explicit global terms -> Accept
    for pat in GLOBAL_PATTERNS:
        if re.search(pat, loc_lower):
            return True

    # 5. If it's simply "Remote" or "Work from Home" without a restrictive country -> Accept
    if any(term in loc_lower for term in ["remote", "work from home", "telecommute", "wfh"]):
        return True

    # Otherwise, if no match with India or Global, reject
    return False
