"""
notification_system/sender/base_sender.py
------------------------------------------
Abstract base class for all output adapters in the notification pipeline.

Defines the contract that every sender implementation must satisfy.
Adding a new output channel requires only implementing this interface —
no other layer needs to change.
"""

from abc import ABC, abstractmethod


class BaseSender(ABC):
    """Abstract base class for all output adapters."""

    @abstractmethod
    def send(self, to: str, message: str) -> bool:
        """
        Send a notification to the specified recipient.

        Args:
            to: Destination address in the format required by the channel
                (e.g., '120363000000000001@g.us' for a WhatsApp group,
                '212600000001@c.us' for an individual number).
            message: Plain-text body of the notification to send.

        Returns:
            True if the message was delivered successfully, False otherwise.
        """
