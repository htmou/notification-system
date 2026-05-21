"""
notification_system/analyzer/content_analyzer.py
-------------------------------------------------
Keyword-based content analyzer for the notification pipeline.

Evaluates a normalized Message against the routing rules defined in
config/routing_rules.yaml and produces a RoutingDecision. Rules are
evaluated in priority order; the first match wins. Falls back to the
configured default target when no rule matches.
"""

import logging
from datetime import datetime

from notification_system.models import Message, RoutingDecision

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """
    Analyzes message content against configurable routing rules.

    Attributes:
        _rules: List of routing rules sorted by priority ascending.
        _fallback_target: WhatsApp group key used when no rule matches.
    """

    def __init__(self, rules: dict) -> None:
        """
        Initialize the analyzer with the loaded routing configuration.

        Args:
            rules: Dictionary returned by get_routing_rules(), containing
                   a 'rules' list and a 'fallback_target' string.
        """
        self._rules: list[dict] = sorted(
            rules["rules"], key=lambda r: r["priority"]
        )
        self._fallback_target: str = rules["fallback_target"]

    def analyze(self, message: Message) -> RoutingDecision:
        """
        Match a message against routing rules and return a routing decision.

        Concatenates subject and body into a single lowercase search text.
        Iterates rules in priority order; the first rule with at least one
        keyword match fires. Confidence is the ratio of matched keywords to
        the total keywords defined in the fired rule.

        Args:
            message: Normalized Message produced by the Input Layer.

        Returns:
            RoutingDecision with the matched rule and target, or a fallback
            decision if no rule matches.
        """
        search_text = f"{message.subject} {message.body}".lower()

        for rule in self._rules:
            matched = [kw for kw in rule["keywords"] if kw.lower() in search_text]
            if matched:
                confidence = round(len(matched) / len(rule["keywords"]), 4)
                logger.info(
                    "Règle '%s' déclenchée — %d/%d mot(s)-clé(s) trouvé(s).",
                    rule["name"],
                    len(matched),
                    len(rule["keywords"]),
                )
                return RoutingDecision(
                    message_id=message.id,
                    category=rule["name"],
                    target=rule["target"],
                    confidence=confidence,
                    matched_rule=rule["name"],
                    is_fallback=False,
                    decided_at=datetime.now(),
                )

        logger.info(
            "Aucune règle correspondante — routage vers la cible de repli '%s'.",
            self._fallback_target,
        )
        return RoutingDecision(
            message_id=message.id,
            category="fallback",
            target=self._fallback_target,
            confidence=0.0,
            matched_rule=None,
            is_fallback=True,
            decided_at=datetime.now(),
        )
