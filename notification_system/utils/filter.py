"""
notification_system/utils/filter.py
-------------------------------------
Keyword-based pre-analysis filter for the notification pipeline.

Applies include and exclude keyword rules to a Message before it enters
the Analysis Layer. The filter logic is:
  1. If an exclude keyword is found in subject or body → reject (skip).
  2. If the include list is non-empty and no include keyword is found → reject.
  3. Otherwise → accept (process normally).

All matching is case-insensitive and searches the concatenation of subject
and body.
"""

from notification_system.models import Message


def should_process(message: Message, filters: dict) -> bool:
    """
    Determine whether a message should enter the analysis pipeline.

    Args:
        message: Normalized Message object to evaluate.
        filters: Dictionary with 'include' and 'exclude' keyword lists.
                 Either list may be empty, in which case its rule is skipped.

    Returns:
        True if the message should be processed, False if it should be skipped.
    """
    text = f"{message.subject} {message.body}".lower()

    exclude = [kw.lower() for kw in filters.get("exclude", [])]
    include = [kw.lower() for kw in filters.get("include", [])]

    if any(kw in text for kw in exclude):
        return False

    if include and not any(kw in text for kw in include):
        return False

    return True
