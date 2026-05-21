"""
notification_system/models.py
------------------------------
Normalized data contracts for the notification pipeline.

Defines Message (the normalized representation of an incoming email)
and RoutingDecision (the output of the analysis and routing layers).
All external data entering the pipeline must be validated against
these models before any further processing occurs.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """
    Normalized representation of an incoming notification source.

    Produced by the Input Layer (BaseReader implementations) and
    consumed by the Analysis Layer. All fields are required — no
    message may enter the pipeline with missing or empty values.

    Attributes:
        id: Unique identifier for this message (e.g., email Message-ID header).
        sender: Email address of the original sender.
        subject: Subject line of the incoming message.
        body: Plain-text body of the message.
        received_at: Timestamp when the message was received by the reader.
        severity: Severity classification — INFO, WARNING, or CRITICAL.
    """

    id: str = Field(min_length=1)
    sender: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    received_at: datetime
    severity: Literal["INFO", "WARNING", "CRITICAL"]


class RoutingDecision(BaseModel):
    """
    Output of the Analysis and Routing layers for a single Message.

    Produced by the Routing Layer and consumed by the Output Layer
    (BaseSender implementations). Records which rule fired, which
    channel was selected, and how confident the router was.

    Attributes:
        message_id: Identifier of the Message this decision applies to.
        category: Matched rule category name (e.g., 'urgent_alert').
        target: WhatsApp target group key (urgent, maintenance, general).
        confidence: Router confidence score, bounded to [0.0, 1.0].
        matched_rule: Name of the routing rule that fired, or None if fallback.
        is_fallback: True when no rule matched and the fallback target was used.
        decided_at: Timestamp when the routing decision was produced.
    """

    message_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    target: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    matched_rule: Optional[str] = None
    is_fallback: bool
    decided_at: datetime
