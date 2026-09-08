import re
from typing import Optional, List

# Explicit technical keywords
TECH_KEYWORDS = [
    "software engineer", "software developer", "frontend", "backend",
    "full stack", "fullstack", "web developer", "python", "react",
    "node", "javascript", "typescript", "golang", "java developer",
    "c++", "data engineer", "data scientist", "machine learning",
    "ai engineer", "ml engineer", "devops", "sre", "cloud engineer",
    "qa engineer", "systems engineer", "mobile developer", "android",
    "ios developer", "firmware", "embedded", "computer science",
    "security engineer", "site reliability", "platform engineer",
    "application developer", "database administrator", "dba",
    "programmer", "api developer", "infrastructure engineer"
]

# Explicit non-technical keywords and categories to strictly reject
NON_TECH_REJECTIONS = [
    r"\bsales\b",
    r"\bmarketing\b",
    r"\bcopywrit(er|ing)\b",
    r"\bcontent writ(er|ing)\b",
    r"\bfreelance writ(er|ing)\b",
    r"\brecruiter\b",
    r"\btalent acquisition\b",
    r"\bhuman resources\b",
    r"\bhr\b",
    r"\blegal\b",
    r"\bcounsel\b",
    r"\battorney\b",
    r"\blawyer\b",
    r"\baccountant\b",
    r"\baccounting\b",
    r"\bfinancial consultant\b",
    r"\bfinance manager\b",
    r"\bcustomer support\b",
    r"\bcustomer service\b",
    r"\bbusiness development\b",
    r"\bbdr\b",
    r"\bsdr\b",
    r"\bproduct support jedi\b",
    r"\bsales jedi\b",
    r"\bsocial media manager\b",
    r"\boffice manager\b",
    r"\bexecutive assistant\b"
]

def is_technical_role(
    title: str,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> bool:
    """Evaluates whether a job posting is a technical CSE / Software Engineering role.
    
    Returns True for engineering, developer, data, ML, cloud, infrastructure roles.
    Returns False for sales, marketing, writing, HR, legal, finance, customer support.
    """
    if not title or not title.strip():
        return False

    title_lower = title.strip().lower()
    cat_lower = (category or "").strip().lower()
    tags_lower = [t.lower() for t in (tags or [])]

    # 1. Reject if category or title matches non-tech pattern
    for pattern in NON_TECH_REJECTIONS:
        if re.search(pattern, title_lower):
            return False
        if cat_lower and re.search(pattern, cat_lower):
            return False

    # 2. If category is explicitly non-tech
    non_tech_cats = ["sales", "marketing", "writing", "customer service", "legal", "hr", "finance"]
    if any(c in cat_lower for c in non_tech_cats):
        return False

    # 3. Check for positive technical signals in title
    if any(kw in title_lower for kw in TECH_KEYWORDS):
        return True

    # 4. Check for technical signals in tags
    tech_tags = ["python", "react", "javascript", "backend", "frontend", "api", "aws", "docker", "c++", "java", "sql"]
    if any(t in tags_lower for t in tech_tags):
        # Only accept if title does not look like a general non-tech role
        if any(w in title_lower for w in ["engineer", "developer", "architect", "programmer", "specialist", "analyst"]):
            return True

    # 5. Internships / Freshers
    if any(w in title_lower for w in ["intern", "trainee", "fresher", "apprentice"]):
        if any(kw in title_lower for kw in ["software", "tech", "code", "dev", "data", "it", "cs", "computer"]):
            return True

    return False
