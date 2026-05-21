"""
notification_system/utils/logger.py
-------------------------------------
Audit logger for the notification pipeline.

Records routing decisions to a persistent log file. Only decision
metadata is written — message content (body, subject, sender) is
never logged under any circumstance. This is a security requirement.
"""

import logging
from pathlib import Path

from notification_system.models import RoutingDecision


class AuditLogger:
    """
    Writes structured audit entries for every routing decision.

    Each entry records decision metadata only: message identifier,
    matched category, target group, confidence score, fallback flag,
    and the rule that fired. No message content is ever written.

    Attributes:
        _logger: Configured Python logger writing to the audit file.
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize the audit logger with the log configuration.

        Creates the log directory if it does not exist. Clears any
        existing handlers before adding a new one to prevent duplicate
        entries when the logger is re-instantiated.

        Args:
            config: Dictionary returned by get_log_config(), containing
                    'log_level' and 'log_file' keys.
        """
        log_file = Path(config["log_file"])
        log_file.parent.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger("ocp.audit")
        self._logger.setLevel(getattr(logging, config["log_level"].upper()))
        self._logger.propagate = False

        self._logger.handlers.clear()
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
        self._logger.addHandler(handler)

    def log_shutdown(self) -> None:
        """Write an audit entry recording the graceful pipeline shutdown event."""
        self._logger.info("SHUTDOWN | pipeline stopped")

    def log_decision(self, decision: RoutingDecision) -> None:
        """
        Write a structured audit entry for a routing decision.

        Args:
            decision: RoutingDecision produced by the Routing Layer.
        """
        self._logger.info(
            "message_id=%s | category=%s | target=%s | confidence=%s | fallback=%s | rule=%s",
            decision.message_id,
            decision.category,
            decision.target,
            decision.confidence,
            decision.is_fallback,
            decision.matched_rule,
        )
