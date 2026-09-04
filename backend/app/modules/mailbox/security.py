import base64
import hashlib
import hmac
import json
import re
import time
import uuid
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from app.core.config import settings

def _get_fernet() -> Fernet:
    """Derives a standard 32-byte URL-safe base64 Fernet key from settings."""
    raw_key = (settings.MAILBOX_ENCRYPTION_KEY or settings.SECRET_KEY).encode("utf-8")
    derived = hashlib.sha256(raw_key).digest()
    b64_key = base64.urlsafe_b64encode(derived)
    return Fernet(b64_key)

def encrypt_token(token: Optional[str]) -> Optional[str]:
    """Encrypts a sensitive OAuth token for safe database persistence."""
    if not token:
        return None
    f = _get_fernet()
    return f.encrypt(token.encode("utf-8")).decode("utf-8")

def decrypt_token(encrypted_token: Optional[str]) -> Optional[str]:
    """Decrypts a persisted token. Returns None if input is empty or invalid."""
    if not encrypted_token:
        return None
    try:
        f = _get_fernet()
        return f.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
    except Exception:
        return None

def generate_oauth_state(user_id: uuid.UUID, provider: str) -> str:
    """Generates an HMAC-signed state token incorporating user_id, provider, timestamp, and nonce."""
    payload = {
        "user_id": str(user_id),
        "provider": provider.lower(),
        "timestamp": int(time.time()),
        "nonce": uuid.uuid4().hex,
    }
    payload_str = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return f"{payload_str}.{signature}"

def validate_oauth_state(state: str, expected_provider: Optional[str] = None, max_age_seconds: int = 600) -> uuid.UUID:
    """
    Validates HMAC signature and expiry for state token.
    Returns the user_id if valid, otherwise raises ValueError.
    """
    if not state or "." not in state:
        raise ValueError("Invalid state format")
    
    parts = state.split(".", 1)
    payload_str, provided_sig = parts[0], parts[1]

    expected_sig = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(provided_sig, expected_sig):
        raise ValueError("State signature mismatch or tampering detected")

    try:
        data = json.loads(base64.urlsafe_b64decode(payload_str.encode("utf-8")).decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Malformed state payload: {exc}")

    # Expiry check
    issued_at = data.get("timestamp", 0)
    now = int(time.time())
    if now - issued_at > max_age_seconds:
        raise ValueError("OAuth state has expired")

    # Provider check
    if expected_provider and data.get("provider") != expected_provider.lower():
        raise ValueError(f"Provider mismatch: expected {expected_provider}, got {data.get('provider')}")

    return uuid.UUID(data["user_id"])

def sanitize_html(raw_html: Optional[str]) -> str:
    """
    Sanitizes HTML content to prevent XSS.
    Strips script tags, event handlers, javascript pseudo-protocols, and unsafe elements.
    """
    if not raw_html:
        return ""
    
    cleaned = raw_html

    # Strip dangerous tag pairs entirely (case insensitive, multiline)
    dangerous_tags = ["script", "iframe", "object", "embed", "applet", "meta", "style", "form", "svg"]
    for tag in dangerous_tags:
        cleaned = re.sub(rf"<{tag}\b[^>]*>([\s\S]*?)<\/{tag}>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(rf"<{tag}\b[^>]*\/?>", "", cleaned, flags=re.IGNORECASE)

    # Strip event handler attributes like onload, onerror, onclick, etc.
    cleaned = re.sub(r'\s+on[a-zA-Z]+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', "", cleaned, flags=re.IGNORECASE)

    # Strip javascript: and vbscript: URIs in href and src
    cleaned = re.sub(r'(href|src)\s*=\s*(["\'])\s*(?:javascript|vbscript|data:text\/html):.*?\2', r'\1="#"', cleaned, flags=re.IGNORECASE)

    return cleaned.strip()
