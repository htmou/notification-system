"""
notification_system/reader/email_reader.py
------------------------------------------
IMAP email reader with TLS encryption.

Connects to the configured mailbox, retrieves unread messages,
and converts them into normalized Message objects for downstream
processing. All connections use SSL on port 993.
"""

import email
import imaplib
import logging
import ssl
import uuid
from datetime import datetime
from email.header import decode_header as _decode_header_raw
from email.utils import parseaddr, parsedate_to_datetime

from pydantic import ValidationError

from notification_system.models import Message
from notification_system.reader.base_reader import BaseReader

logger = logging.getLogger(__name__)


class EmailReader(BaseReader):
    """
    IMAP email reader that fetches UNSEEN messages and normalizes them.

    Attributes:
        _server: IMAP server hostname.
        _port: IMAP server port (993 for SSL).
        _email: Email address used to authenticate.
        _password: App password for IMAP authentication.
        _folder: IMAP folder to monitor.
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize the reader with connection parameters.

        Args:
            config: Dictionary returned by get_email_config(), containing
                    imap_server, imap_port, email_address, email_password,
                    and email_folder keys.
        """
        self._server: str = config["imap_server"]
        self._port: int = config["imap_port"]
        self._email: str = config["email_address"]
        self._password: str = config["email_password"]
        self._folders: list[str] = config["email_folders"]

    def read_messages(self) -> list[Message]:
        """
        Connect to the IMAP server, fetch all UNSEEN messages, and return
        them as normalized Message objects.

        Each successfully parsed message is marked as \\Seen before the
        connection closes. Severity defaults to INFO — the content analyzer
        determines the final severity in the Analysis Layer.

        Returns:
            List of Message objects. Empty if no unread messages are found.

        Raises:
            ConnectionError: If the IMAP connection or login fails.
        """
        ssl_context = ssl.create_default_context()
        messages: list[Message] = []

        try:
            conn = imaplib.IMAP4_SSL(self._server, self._port, ssl_context=ssl_context)
        except (imaplib.IMAP4.error, OSError) as exc:
            raise ConnectionError(
                f"Impossible de se connecter au serveur IMAP "
                f"'{self._server}:{self._port}' : {exc}"
            ) from exc

        try:
            try:
                conn.login(self._email, self._password)
            except imaplib.IMAP4.error as exc:
                raise ConnectionError(
                    f"Échec de l'authentification IMAP pour '{self._email}' : {exc}"
                ) from exc

            for folder in self._folders:
                select_status, _ = conn.select(folder)
                if select_status != "OK":
                    logger.warning("Dossier IMAP inaccessible, ignoré : '%s'.", folder)
                    continue

                status, data = conn.search(None, "UNSEEN")
                if status != "OK" or not data[0]:
                    logger.info("Aucun message non lu dans le dossier '%s'.", folder)
                    continue

                uids = data[0].split()
                logger.info("%d message(s) non lu(s) trouvé(s) dans '%s'.", len(uids), folder)

                for uid in uids:
                    status, raw = conn.fetch(uid, "(RFC822)")
                    if status != "OK" or not raw or not isinstance(raw[0], tuple):
                        continue

                    raw_bytes = raw[0][1]
                    parsed = email.message_from_bytes(raw_bytes)

                    try:
                        msg = Message(
                            id=self._extract_message_id(parsed),
                            sender=self._extract_sender(parsed),
                            subject=self._decode_header(parsed.get("Subject", "")) or "(Sans objet)",
                            body=self._extract_plain_body(parsed),
                            received_at=self._extract_received_at(parsed),
                            severity="INFO",
                        )
                        messages.append(msg)
                        conn.store(uid, "+FLAGS", "\\Seen")
                    except ValidationError:
                        logger.warning(
                            "Message ignoré — données insuffisantes pour construire "
                            "un objet Message valide (expéditeur ou corps absent)."
                        )

        finally:
            try:
                conn.close()
            except Exception:
                pass
            try:
                conn.logout()
            except Exception:
                pass

        return messages

    def close(self) -> None:
        """
        No-op — IMAP connections are opened and closed per read_messages() call.

        Implements the BaseReader.close() contract for graceful shutdown.
        No persistent connection is held between polling cycles.
        """

    def _extract_received_at(self, msg: email.message.Message) -> datetime:
        """Parse the Date: header to a datetime, falling back to now() if absent or malformed."""
        date_str = msg.get("Date", "")
        if date_str:
            try:
                return parsedate_to_datetime(date_str)
            except Exception:
                pass
        return datetime.now()

    def _extract_sender(self, msg: email.message.Message) -> str:
        """Parse the From: header into 'Name <addr>' or bare 'addr' format."""
        decoded = self._decode_header(msg.get("From", ""))
        name, addr = parseaddr(decoded)
        if name:
            return f"{name} <{addr}>"
        return addr

    def _decode_header(self, value: str) -> str:
        """Decode a potentially RFC 2047-encoded email header into plain text."""
        parts = _decode_header_raw(value)
        decoded_parts = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded_parts.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded_parts.append(part)
        return "".join(decoded_parts).strip()

    def _extract_message_id(self, msg: email.message.Message) -> str:
        """Extract and clean the Message-ID header, or generate a UUID fallback."""
        raw_id = msg.get("Message-ID", "")
        cleaned = raw_id.strip().strip("<>")
        return cleaned if cleaned else str(uuid.uuid4())

    def _extract_plain_body(self, msg: email.message.Message) -> str:
        """
        Walk the email parts and return the first text/plain content found.

        Returns an empty string if no plain-text part is found, which will
        cause Pydantic validation to reject the message — intentional, since
        a bodyless message should not enter the pipeline.
        """
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = part.get("Content-Disposition", "")
                if content_type == "text/plain" and "attachment" not in disposition:
                    charset = part.get_content_charset() or "utf-8"
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(charset, errors="replace").strip()
        else:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode(charset, errors="replace").strip()
        return ""
