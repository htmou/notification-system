"""
notification_system/reader/base_reader.py
-----------------------------------------
Abstract base class for all input adapters in the notification pipeline.

Defines the contract that every reader implementation must satisfy.
Adding a new input source requires only implementing this interface —
no other layer needs to change.
"""

from abc import ABC, abstractmethod

from notification_system.models import Message


class BaseReader(ABC):
    """Abstract base class for all input adapters."""

    @abstractmethod
    def read_messages(self) -> list[Message]:
        """
        Fetch and return all new unread messages since the last call.

        Returns:
            List of normalized Message objects ready for the Analysis Layer.
            Returns an empty list if no new messages are available.
        """

    @abstractmethod
    def close(self) -> None:
        """
        Release any persistent resources held by the reader.

        Called once during graceful shutdown to ensure all connections
        and file handles are properly closed before the process exits.
        """
