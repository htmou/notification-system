"""
notification_system/utils/formatter.py
---------------------------------------
WhatsApp message formatter for the notification pipeline.

Converts a Message and RoutingDecision into a structured, WhatsApp-ready
notification string: bold subject header, monospace metadata lines (display
name, email address, and timestamp each on their own line), a blank-line
separator, the plain-text body, and any URLs found in the body appended as
plain clickable links. The output is capped at the native WhatsApp character
limit.
"""

import re
from email.utils import parseaddr

from notification_system.models import Message, RoutingDecision

# Native WhatsApp message limit — previously capped at 1600 characters by
# the outgoing API integration constraint (error 21617), no longer applicable.
_MAX_WHATSAPP_BODY_LENGTH = 4096

# Matches http:// and https:// URLs — used to extract links from the message body.
_URL_PATTERN = re.compile(r"https?://\S+")


def _extract_urls(text: str) -> list[str]:
    """Extract unique URLs from text, stripping trailing sentence punctuation."""
    seen: dict[str, None] = {}
    for raw in _URL_PATTERN.findall(text):
        url = raw.rstrip(".,;:!?)>]'\"")
        seen[url] = None  # preserves insertion order, deduplicates
    return list(seen.keys())


def format_whatsapp_message(message: Message, decision: RoutingDecision) -> str:
    """
    Format a Message and RoutingDecision into a WhatsApp-ready notification string.

    Produces a structured message with:
    - Subject in bold using WhatsApp asterisk syntax (*subject*)
    - Display name on its own monospace line (only when present)
    - Email address on its own monospace line
    - Timestamp on its own monospace line
    - A blank line separating the metadata from the body
    - The plain-text message body
    - Any URLs found in the body appended as plain clickable links

    The result is truncated to the native WhatsApp character limit (4096 characters).

    Args:
        message: Normalized Message object from the Input Layer.
        decision: RoutingDecision produced by the Analysis Layer.

    Returns:
        Formatted notification string, at most 4096 characters long.
    """
    ts = message.received_at
    if ts.tzinfo is not None:
        ts = ts.astimezone()
    timestamp = ts.strftime("%d/%m/%Y %H:%M")

    display_name, address = parseaddr(message.sender)
    urls = _extract_urls(message.body)

    parts = [f"*{message.subject}*"]
    if display_name:
        parts.append(display_name)
    parts.append(address or message.sender)
    parts.append(timestamp)
    parts.append("")
    parts.append(message.body)

    if urls:
        parts.append("")
        parts.extend(urls)

    return "\n".join(parts)[:_MAX_WHATSAPP_BODY_LENGTH]
