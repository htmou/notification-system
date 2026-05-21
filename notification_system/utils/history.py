"""
notification_system/utils/history.py
--------------------------------------
In-memory routing history for the console panel.

Maintains a fixed-size log of the most recent routing decisions,
including delivery status. Rendered as a rich Table for display
in the terminal after each polling cycle that processes at least
one message.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime

from rich import box
from rich.table import Table

_SUBJECT_MAX_LENGTH = 40


@dataclass
class HistoryEntry:
    """A single routing decision recorded in the history panel."""

    subject: str
    category: str
    target: str
    decided_at: datetime
    delivered: bool


class RoutingHistory:
    """
    Fixed-size in-memory log of recent routing decisions.

    Attributes:
        _max_entries: Maximum number of entries to retain.
        _entries: Deque of HistoryEntry objects; oldest dropped when full.
    """

    def __init__(self, max_entries: int = 10) -> None:
        """
        Initialize the history with a configurable capacity.

        Args:
            max_entries: Maximum number of entries to retain. The oldest
                         entry is discarded when the limit is exceeded.
        """
        self._max_entries = max_entries
        self._entries: deque[HistoryEntry] = deque(maxlen=max_entries)

    def record(
        self,
        subject: str,
        category: str,
        target: str,
        decided_at: datetime,
        delivered: bool,
    ) -> None:
        """
        Add a routing decision to the history.

        Subjects longer than _SUBJECT_MAX_LENGTH are truncated with an
        ellipsis to keep the table readable on a terminal.

        Args:
            subject: Email subject line.
            category: Routing category assigned by the analyzer.
            target: Target group key resolved by the router.
            decided_at: Timestamp of the routing decision.
            delivered: True if Green API accepted the message.
        """
        if len(subject) > _SUBJECT_MAX_LENGTH:
            subject = subject[: _SUBJECT_MAX_LENGTH - 1] + "…"
        self._entries.append(
            HistoryEntry(
                subject=subject,
                category=category,
                target=target,
                decided_at=decided_at,
                delivered=delivered,
            )
        )

    def as_table(self) -> Table:
        """
        Render the history as a rich Table, most recent entry first.

        Returns:
            A rich Table ready to be printed to the console.
        """
        table = Table(
            title="Historique des notifications",
            box=box.SIMPLE_HEAD,
            show_lines=False,
            expand=False,
        )
        table.add_column("Heure", style="dim", width=10)
        table.add_column("Sujet", width=42)
        table.add_column("Catégorie", width=20)
        table.add_column("Groupe", width=14)
        table.add_column("Statut", width=6, justify="center")

        for entry in reversed(self._entries):
            status_icon = "✓" if entry.delivered else "✗"
            status_style = "green" if entry.delivered else "red"
            table.add_row(
                entry.decided_at.strftime("%H:%M:%S"),
                entry.subject,
                entry.category,
                entry.target,
                f"[{status_style}]{status_icon}[/{status_style}]",
            )

        return table

    @property
    def entries(self) -> list[HistoryEntry]:
        """Return a snapshot of all current entries, oldest first."""
        return list(self._entries)

    def __len__(self) -> int:
        """Return the number of entries currently in the history."""
        return len(self._entries)
