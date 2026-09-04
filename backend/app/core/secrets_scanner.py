import re
from typing import List, Dict, Any, Tuple

# Patterns for discovering accidental secrets in text/logs/payloads
SECRET_PATTERNS = [
    (re.compile(r"Bearer\s+([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE), "BEARER_TOKEN"),
    (re.compile(r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*"), "JWT_TOKEN"),
    (re.compile(r"-----BEGIN[ A-Z0-9_-]*PRIVATE KEY-----[\s\S]*?-----END[ A-Z0-9_-]*PRIVATE KEY-----"), "PRIVATE_KEY"),
    (re.compile(r"(?:api[_-]?key|secret[_-]?key|client[_-]?secret)\s*[:=]\s*['\"]?([A-Za-z0-9\-_]{16,})['\"]?", re.IGNORECASE), "API_KEY_OR_SECRET"),
    (re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{6,})['\"]?", re.IGNORECASE), "PASSWORD"),
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OPENAI_API_KEY"),
    (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "GOOGLE_API_KEY"),
]

class SecretScanner:
    """Detects and redacts secrets in logs, responses, and test fixtures."""

    @staticmethod
    def find_secrets(text: str) -> List[Tuple[str, str]]:
        """Returns list of (secret_type, matched_snippet_masked) found in text."""
        if not text:
            return []
        findings = []
        for pattern, secret_type in SECRET_PATTERNS:
            matches = pattern.findall(text)
            for m in matches:
                val = m if isinstance(m, str) else str(m)
                masked = val[:3] + "..." + val[-3:] if len(val) > 6 else "[REDACTED]"
                findings.append((secret_type, masked))
        return findings

    @staticmethod
    def contains_secrets(text: str) -> bool:
        """Returns True if any secret pattern is matched in text."""
        if not text:
            return False
        for pattern, _ in SECRET_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @staticmethod
    def redact_secrets(text: str) -> str:
        """Redacts all discovered secrets from text."""
        if not text:
            return ""
        sanitized = text
        for pattern, secret_type in SECRET_PATTERNS:
            sanitized = pattern.sub(f"[{secret_type}_REDACTED]", sanitized)
        return sanitized
