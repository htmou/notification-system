"""
notification_system/router/router.py
-------------------------------------
Routing Layer — resolves a RoutingDecision to a concrete WhatsApp recipient.

Accepts the RoutingDecision produced by the Analysis Layer and maps its
target group key (urgent, maintenance, general) to the corresponding
WhatsApp phone number defined in the environment configuration. Raises
ValueError for any target key not present in the configured groups.
"""

import logging

from notification_system.models import RoutingDecision
from shared.config_loader import DEFAULT_WHATSAPP_GROUP

logger = logging.getLogger(__name__)


class Router:
    """
    Resolves a RoutingDecision's target key to a WhatsApp phone number.

    Attributes:
        _groups: Mapping of group keys to WhatsApp phone numbers,
                 as returned by get_whatsapp_groups().
    """

    def __init__(self, groups: dict) -> None:
        """
        Initialize the router with the WhatsApp group configuration.

        Args:
            groups: Dictionary mapping group keys (urgent, maintenance,
                    general) to their WhatsApp phone numbers.
        """
        self._groups: dict[str, str] = groups

    def route(self, decision: RoutingDecision) -> str:
        """
        Resolve a routing decision to a concrete WhatsApp phone number.

        If the decision's target key is not found, falls back to
        DEFAULT_WHATSAPP_GROUP before raising ValueError.

        Args:
            decision: RoutingDecision produced by the Analysis Layer.

        Returns:
            WhatsApp phone number string for the resolved target group.

        Raises:
            ValueError: If neither the target key nor DEFAULT_WHATSAPP_GROUP
                        is present in the configured WhatsApp groups.
        """
        target = decision.target
        if target in self._groups:
            number = self._groups[target]
        elif DEFAULT_WHATSAPP_GROUP in self._groups:
            logger.warning(
                "Cible de routage '%s' inconnue — repli vers le groupe par défaut '%s'.",
                target,
                DEFAULT_WHATSAPP_GROUP,
            )
            number = self._groups[DEFAULT_WHATSAPP_GROUP]
        else:
            raise ValueError(
                f"Cible de routage inconnue : '{target}' et le groupe de repli "
                f"'{DEFAULT_WHATSAPP_GROUP}' n'est pas configuré. "
                f"Cibles configurées : {list(self._groups.keys())}."
            )
        logger.info(
            "Message '%s' acheminé vers le groupe '%s'.",
            decision.message_id,
            target,
        )
        return number
