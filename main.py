"""
main.py
--------
Pipeline orchestrator for the OCP ML Monitoring notification system.

Initializes all pipeline components from the centralized configuration,
schedules periodic email polling, and coordinates the full processing
cycle: read → sanitize → analyze → route → send → log.

Keyboard shortcuts (Windows):
  P — toggle pause / resume polling
  Q — graceful shutdown
"""

import logging
import msvcrt
import signal
import sys
import threading
import time

import schedule
from rich.console import Console
from rich.logging import RichHandler

from notification_system.analyzer.content_analyzer import ContentAnalyzer
from notification_system.reader.base_reader import BaseReader
from notification_system.reader.email_reader import EmailReader
from notification_system.router.router import Router
from notification_system.sender.base_sender import BaseSender
from notification_system.sender.whatsapp_sender import WhatsAppSender
from notification_system.utils.filter import should_process
from notification_system.utils.formatter import format_whatsapp_message
from notification_system.utils.history import RoutingHistory
from notification_system.utils.logger import AuditLogger
from notification_system.utils.validator import sanitize_message
from shared.config_loader import (
    get_app_config,
    get_email_config,
    get_filters,
    get_imap_folders,
    get_log_config,
    get_routing_rules,
    get_green_api_config,
    get_whatsapp_groups,
)

console = Console()

logging.basicConfig(
    level=logging.INFO,
    handlers=[RichHandler(console=console, show_path=False)],
)
logger = logging.getLogger(__name__)


def run_pipeline(
    reader: BaseReader,
    analyzer: ContentAnalyzer,
    router: Router,
    sender: BaseSender,
    audit_logger: AuditLogger,
    filters: dict | None = None,
    history: RoutingHistory | None = None,
) -> None:
    """
    Execute one polling cycle of the notification pipeline.

    Reads new messages, sanitizes them, applies keyword filters, produces a
    routing decision, resolves the target recipient, sends the WhatsApp
    notification, and writes an audit log entry. Skips messages with invalid
    sender format or that do not pass the configured keyword filters.
    Logs and continues if the email connection fails.

    After processing, prints an updated history panel if any messages were
    routed and a history object was provided.

    Args:
        reader: Input adapter that fetches new messages.
        analyzer: Content analyzer that produces routing decisions.
        router: Router that resolves target keys to phone numbers.
        sender: Output adapter that delivers WhatsApp notifications.
        audit_logger: Audit logger that records routing decisions.
        filters: Keyword filter dict with 'include' and 'exclude' lists.
                 If None or both lists are empty, all messages are processed.
        history: Optional routing history panel updated after each delivery.
    """
    active_filters = filters or {}
    any_recorded = False

    try:
        messages = reader.read_messages()
    except ConnectionError as exc:
        logger.error("Échec de connexion au serveur email : %s", exc)
        return

    for message in messages:
        try:
            message = sanitize_message(message)
        except ValueError as exc:
            logger.warning("Message ignoré — expéditeur invalide : %s", exc)
            continue

        if not should_process(message, active_filters):
            logger.info("Message filtré — ne correspond pas aux filtres configurés.")
            continue

        decision = analyzer.analyze(message)
        try:
            recipient = router.route(decision)
        except ValueError as exc:
            logger.error(
                "Cible de routage inconnue '%s' — message ignoré : %s",
                decision.target,
                exc,
            )
            continue

        notification_body = format_whatsapp_message(message, decision)
        delivered = sender.send(recipient, notification_body)
        audit_logger.log_decision(decision)

        if history is not None:
            history.record(
                subject=message.subject,
                category=decision.category,
                target=decision.target,
                decided_at=decision.decided_at,
                delivered=delivered,
            )
            any_recorded = True

    if history is not None and any_recorded:
        console.print(history.as_table())


def toggle_pause(running_event: threading.Event) -> bool:
    """
    Toggle the pipeline polling between paused and running states.

    Args:
        running_event: Shared threading.Event used as a polling gate.

    Returns:
        True if polling is now paused, False if polling is now running.
    """
    if running_event.is_set():
        running_event.clear()
        logger.info("Polling mis en pause. Appuyez sur [P] pour reprendre.")
        console.print("[bold yellow]⏸  EN PAUSE[/bold yellow]")
        return True
    else:
        running_event.set()
        logger.info("Polling repris.")
        console.print("[bold green]▶  EN COURS[/bold green]")
        return False


def _keyboard_listener(running_event: threading.Event, shutdown_event: threading.Event) -> None:
    """Poll the keyboard in a background thread; P toggles pause, Q requests shutdown (Windows only)."""
    while not shutdown_event.is_set():
        if msvcrt.kbhit():
            key = msvcrt.getwch()
            if key.lower() == "p":
                toggle_pause(running_event)
            elif key.lower() == "q":
                shutdown_event.set()
        time.sleep(0.1)


def _shutdown(reader: BaseReader, audit_logger: AuditLogger) -> None:
    """
    Perform a graceful shutdown: log the event, close the reader, print confirmation.

    Args:
        reader: Input adapter to close.
        audit_logger: Audit logger that records the shutdown event.
    """
    console.print("[bold red]⏹  ARRÊT EN COURS...[/bold red]")
    audit_logger.log_shutdown()
    reader.close()
    logger.info("Pipeline arrêté proprement.")
    console.print("[bold red]Au revoir.[/bold red]")


def _display_startup_config(folders: list[str], filters: dict) -> None:
    """Print the active folder and filter configuration to the console at startup."""
    console.print(f"  [bold]Dossiers surveillés :[/bold] {', '.join(folders)}")

    include = filters.get("include", [])
    exclude = filters.get("exclude", [])

    if not include and not exclude:
        console.print("  [dim]Filtres : Aucun filtre — tous les emails sont traités.[/dim]")
    else:
        if include:
            console.print(f"  [bold]Filtres inclusion :[/bold] {', '.join(include)}")
        if exclude:
            console.print(f"  [bold]Filtres exclusion :[/bold] {', '.join(exclude)}")


def build_pipeline() -> tuple[BaseReader, ContentAnalyzer, Router, BaseSender, AuditLogger]:
    """
    Instantiate and return all pipeline components from the configuration.

    Returns:
        Tuple of (reader, analyzer, router, sender, audit_logger).
    """
    reader = EmailReader(get_email_config())
    analyzer = ContentAnalyzer(get_routing_rules())
    router = Router(get_whatsapp_groups())
    sender = WhatsAppSender(get_green_api_config())
    audit_logger = AuditLogger(get_log_config())
    return reader, analyzer, router, sender, audit_logger


def main() -> None:
    """
    Entry point — build the pipeline, schedule polling, and run the loop.
    """
    try:
        app_config = get_app_config()
        interval = app_config["polling_interval"]
        filters = get_filters()
        reader, analyzer, router, sender, audit_logger = build_pipeline()
    except EnvironmentError as exc:
        console.print(
            f"[bold red]Erreur de configuration :[/bold red] {exc}\n"
            "Vérifiez que le fichier .env est présent à la racine du projet "
            "et que toutes les variables requises y sont définies."
        )
        logger.debug("Détail de l'erreur de configuration :", exc_info=True)
        sys.exit(1)

    console.rule("[bold blue]OCP ML Monitoring — Notification System[/bold blue]")
    logger.info("Environnement : %s", app_config["app_env"])
    logger.info("Intervalle de polling : %d secondes.", interval)
    _display_startup_config(get_imap_folders(), filters)

    if not sender.check_instance():
        console.print(
            "[bold yellow]⚠  AVERTISSEMENT : l'instance WhatsApp Green API est hors ligne.[/bold yellow]\n"
            "   Les notifications ne seront pas délivrées tant que l'instance n'est pas reconnectée.\n"
            "   Reconnectez-la via le dashboard Green API (QR code)."
        )

    history = RoutingHistory(max_entries=10)

    schedule.every(interval).seconds.do(
        run_pipeline, reader, analyzer, router, sender, audit_logger, filters, history
    )

    running_event = threading.Event()
    running_event.set()
    shutdown_event = threading.Event()

    signal.signal(signal.SIGINT, lambda _sig, _frame: shutdown_event.set())

    listener = threading.Thread(
        target=_keyboard_listener,
        args=(running_event, shutdown_event),
        daemon=True,
    )
    listener.start()

    logger.info("Pipeline démarré. [P] pause · [Q] arrêt.")

    try:
        while not shutdown_event.is_set():
            if running_event.is_set():
                schedule.run_pending()
            time.sleep(1)
    finally:
        _shutdown(reader, audit_logger)


if __name__ == "__main__":
    main()
