"""
notification_system/sender/whatsapp_sender.py
----------------------------------------------
WhatsApp output adapter for the notification pipeline.

Sends notifications to WhatsApp individuals and groups via the Green API
REST endpoint. All credentials are loaded through shared/config_loader.py.
Message content is never written to logs.
"""

import logging

import requests

from notification_system.sender.base_sender import BaseSender

_GREEN_API_BASE_URL = "https://api.green-api.com"

logger = logging.getLogger(__name__)


class WhatsAppSender(BaseSender):
    """
    Sends WhatsApp messages via the Green API REST endpoint.

    Supports both individual recipients (number@c.us) and native WhatsApp
    groups (groupId@g.us) without any difference at the code level.

    Attributes:
        _instance_id: Green API instance identifier.
        _api_token: Green API authentication token for the instance.
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize the sender with Green API credentials.

        Args:
            config: Dictionary returned by get_green_api_config(), containing
                    'instance_id' and 'api_token' keys.
        """
        self._instance_id: str = config["instance_id"]
        self._api_token: str = config["api_token"]

    def check_instance(self) -> bool:
        """
        Check whether the Green API WhatsApp instance is online and authorized.

        Calls the getStateInstance endpoint and returns True only when the
        reported state is 'authorized'. Any other state, HTTP error, network
        failure, or malformed response returns False.

        Returns:
            True if the instance is authorized and ready to send messages,
            False for any other state or if the request fails.
        """
        url = (
            f"{_GREEN_API_BASE_URL}"
            f"/waInstance{self._instance_id}"
            f"/getStateInstance/{self._api_token}"
        )
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            state = response.json().get("stateInstance", "")
            if state == "authorized":
                logger.info("Instance Green API autorisée et en ligne.")
                return True
            logger.warning(
                "Instance Green API hors ligne — état : '%s'.", state
            )
            return False
        except requests.HTTPError as exc:
            status = (
                exc.response.status_code
                if exc.response is not None
                else "inconnu"
            )
            logger.error(
                "Erreur HTTP lors de la vérification de l'instance — statut : %s.", status
            )
            return False
        except requests.ConnectionError:
            logger.error("Erreur de connexion lors de la vérification de l'instance.")
            return False
        except requests.Timeout:
            logger.error("Délai dépassé lors de la vérification de l'instance.")
            return False
        except ValueError:
            logger.error("Réponse non-JSON reçue lors de la vérification de l'instance.")
            return False

    def send(self, to: str, message: str) -> bool:
        """
        Send a WhatsApp message to the specified chatId via Green API.

        Args:
            to: Destination chatId — either 'number@c.us' for an individual
                or 'groupId@g.us' for a native WhatsApp group.
            message: Plain-text body of the notification to send.

        Returns:
            True if Green API accepted the message and returned an idMessage,
            False if an HTTP error, connection failure, timeout, or non-JSON
            response body occurred.
        """
        url = (
            f"{_GREEN_API_BASE_URL}"
            f"/waInstance{self._instance_id}"
            f"/sendMessage/{self._api_token}"
        )
        payload = {"chatId": to, "message": message}

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "idMessage" in data:
                logger.info("Message WhatsApp envoyé vers '%s'.", to)
                return True
            logger.error(
                "Green API n'a pas retourné 'idMessage' pour '%s'.", to
            )
            return False
        except requests.HTTPError as exc:
            status = (
                exc.response.status_code
                if exc.response is not None
                else "inconnu"
            )
            logger.error(
                "Erreur HTTP lors de l'envoi WhatsApp vers '%s' — statut : %s.",
                to,
                status,
            )
            return False
        except requests.ConnectionError:
            logger.error(
                "Erreur de connexion lors de l'envoi WhatsApp vers '%s'.", to
            )
            return False
        except requests.Timeout:
            logger.error(
                "Délai d'attente dépassé lors de l'envoi WhatsApp vers '%s'.", to
            )
            return False
        except ValueError:
            logger.error(
                "Réponse Green API non-JSON reçue pour '%s' — envoi considéré comme échoué.", to
            )
            return False
