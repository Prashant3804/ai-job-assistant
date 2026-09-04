import base64
from datetime import datetime, timezone
import email.utils
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.modules.mailbox.security import sanitize_html

class NormalizedEmail(BaseModel):
    external_message_id: str
    external_thread_id: Optional[str] = None
    sender_email: str
    sender_name: Optional[str] = None
    recipient_email: str = "candidate@example.com"
    subject: str
    snippet: str = ""
    body_text: str = ""
    body_html: Optional[str] = None
    received_at: datetime
    has_attachments: bool = False
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    raw_headers: Dict[str, str] = Field(default_factory=dict)

def _parse_email_address(raw_from: str) -> tuple[Optional[str], str]:
    """Extracts (name, email) from header string like 'Jane Doe <jane@company.com>'."""
    if not raw_from:
        return None, "unknown@example.com"
    name, addr = email.utils.parseaddr(raw_from)
    name = name.strip() if name else None
    addr = addr.strip().lower() if addr else raw_from.strip().lower()
    return name, addr

def _decode_gmail_body(data: Optional[str]) -> str:
    """Decodes URL-safe base64 Gmail body part."""
    if not data:
        return ""
    try:
        padded = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="replace")
    except Exception:
        return ""

def _extract_gmail_parts(payload: Dict[str, Any]) -> tuple[str, str, List[Dict[str, Any]]]:
    """Recursively traverses Gmail MIME parts to extract text, html, and attachment metadata."""
    body_text = ""
    body_html = ""
    attachments = []

    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")

    if mime_type == "text/plain" and data:
        body_text += _decode_gmail_body(data)
    elif mime_type == "text/html" and data:
        body_html += _decode_gmail_body(data)

    if payload.get("filename"):
        attachments.append({
            "filename": payload.get("filename"),
            "mime_type": mime_type,
            "size": body.get("size", 0),
            "attachment_id": body.get("attachmentId"),
        })

    for part in payload.get("parts", []):
        sub_text, sub_html, sub_att = _extract_gmail_parts(part)
        if sub_text:
            body_text += "\n" + sub_text
        if sub_html:
            body_html += "\n" + sub_html
        attachments.extend(sub_att)

    return body_text.strip(), body_html.strip(), attachments

def normalize_gmail_message(raw_msg: Dict[str, Any]) -> NormalizedEmail:
    """Normalizes raw Gmail REST API message resource into NormalizedEmail."""
    msg_id = raw_msg.get("id", "")
    thread_id = raw_msg.get("threadId")
    snippet = raw_msg.get("snippet", "")
    internal_date_ms = raw_msg.get("internalDate")

    if internal_date_ms:
        received_at = datetime.fromtimestamp(int(internal_date_ms) / 1000.0, tz=timezone.utc)
    else:
        received_at = datetime.now(timezone.utc)

    payload = raw_msg.get("payload", {})
    headers = {h.get("name", "").lower(): h.get("value", "") for h in payload.get("headers", [])}

    raw_from = headers.get("from", "")
    sender_name, sender_email = _parse_email_address(raw_from)
    
    raw_to = headers.get("to", "candidate@example.com")
    _, recipient_email = _parse_email_address(raw_to)
    
    subject = headers.get("subject", "(No Subject)")

    body_text, body_html, attachments = _extract_gmail_parts(payload)
    if not body_text and snippet:
        body_text = snippet

    sanitized_html = sanitize_html(body_html) if body_html else None

    return NormalizedEmail(
        external_message_id=msg_id,
        external_thread_id=thread_id,
        sender_email=sender_email,
        sender_name=sender_name,
        recipient_email=recipient_email,
        subject=subject,
        snippet=snippet,
        body_text=body_text,
        body_html=sanitized_html,
        received_at=received_at,
        has_attachments=len(attachments) > 0,
        attachments=attachments,
        raw_headers=headers,
    )

def normalize_microsoft_message(raw_msg: Dict[str, Any]) -> NormalizedEmail:
    """Normalizes raw Microsoft Graph API message resource into NormalizedEmail."""
    msg_id = raw_msg.get("id", "")
    thread_id = raw_msg.get("conversationId")
    subject = raw_msg.get("subject", "(No Subject)")
    snippet = raw_msg.get("bodyPreview", "")
    
    from_dict = raw_msg.get("from", {}).get("emailAddress", {})
    sender_name = from_dict.get("name")
    sender_email = (from_dict.get("address") or "unknown@example.com").lower()

    to_recipients = raw_msg.get("toRecipients", [])
    recipient_email = "candidate@example.com"
    if to_recipients:
        recipient_email = to_recipients[0].get("emailAddress", {}).get("address", recipient_email).lower()

    received_str = raw_msg.get("receivedDateTime")
    if received_str:
        try:
            received_at = datetime.fromisoformat(received_str.replace("Z", "+00:00"))
        except Exception:
            received_at = datetime.now(timezone.utc)
    else:
        received_at = datetime.now(timezone.utc)

    body_obj = raw_msg.get("body", {})
    body_content = body_obj.get("content", "")
    content_type = body_obj.get("contentType", "text").lower()

    if content_type == "html":
        body_html = sanitize_html(body_content)
        # Simple plain text fallback from html
        body_text = re.sub(r"<[^>]+>", " ", body_content).strip()
    else:
        body_text = body_content
        body_html = None

    has_attachments = bool(raw_msg.get("hasAttachments", False))
    attachments = []
    if has_attachments and "attachments" in raw_msg:
        for att in raw_msg.get("attachments", []):
            attachments.append({
                "filename": att.get("name"),
                "mime_type": att.get("contentType"),
                "size": att.get("size", 0),
                "attachment_id": att.get("id"),
            })

    return NormalizedEmail(
        external_message_id=msg_id,
        external_thread_id=thread_id,
        sender_email=sender_email,
        sender_name=sender_name,
        recipient_email=recipient_email,
        subject=subject,
        snippet=snippet,
        body_text=body_text,
        body_html=body_html,
        received_at=received_at,
        has_attachments=has_attachments,
        attachments=attachments,
        raw_headers={},
    )
