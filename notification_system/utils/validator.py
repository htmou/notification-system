"""
notification_system/utils/validator.py
----------------------------------------
Input sanitization utilities for the notification pipeline.

Applies sanitization to raw string values and normalized Message objects
before they enter downstream processing. These functions are the last
line of defence against malformed or oversized input at the pipeline
entry point.
"""

from notification_system.models import Message

_MAX_SUBJECT_LENGTH = 500
_MAX_BODY_LENGTH = 2000


def sanitize_text(text: str, max_length: int) -> str:
    """
    Strip leading and trailing whitespace and truncate to max_length.

    Args:
        text: Raw string to sanitize.
        max_length: Maximum number of characters to keep.

    Returns:
        Sanitized string, at most max_length characters long.
    """
    return text.strip()[:max_length]


def validate_sender(sender: str) -> bool:
    """
    Return True if sender looks like a valid email address.

    Checks that the string contains exactly one '@' character and that
    the domain part contains at least one dot.

    Args:
        sender: Email address string to validate.

    Returns:
        True if the basic format is valid, False otherwise.
    """
    parts = sender.split("@")
    if len(parts) != 2:
        return False
    return "." in parts[1]


def sanitize_message(message: Message) -> Message:
    """
    Return a sanitized copy of the message with cleaned string fields.

    Applies sanitize_text to subject and body. Validates the sender
    format and raises ValueError if it does not look like an email
    address.

    Args:
        message: Normalized Message object from the Input Layer.

    Returns:
        New Message instance with sanitized subject and body.

    Raises:
        ValueError: If the sender field does not contain a valid email
                    address format.
    """
    if not validate_sender(message.sender):
        raise ValueError(
            f"Format d'expéditeur invalide : '{message.sender}'. "
            f"Un expéditeur valide doit contenir un '@' et un domaine avec un point."
        )
    return message.model_copy(
        update={
            "subject": sanitize_text(message.subject, _MAX_SUBJECT_LENGTH),
            "body": sanitize_text(message.body, _MAX_BODY_LENGTH),
        }
    )
