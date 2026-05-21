"""
shared/config_loader.py
-----------------------
Module centralisé de chargement et de validation de la configuration.

Toutes les variables d'environnement du projet doivent être accédées
via ce module. Aucun autre fichier ne doit importer directement
os.environ ou python-dotenv.
"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Chargement du fichier .env
_PROJECT_ROOT = Path(__file__).parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=_ENV_FILE)

# Constantes publiques
DEFAULT_IMAP_FOLDER = "INBOX"
DEFAULT_WHATSAPP_GROUP = "general"

# Constante privée — préfixe de convention pour les groupes WhatsApp
_WHATSAPP_GROUP_PREFIX = "WHATSAPP_GROUP_"

# Fonction utilitaire de récupération sécurisée


def _get_required(key: str) -> str:
    """
    Récupère la valeur d'une variable d'environnement requise.

    Si la variable est absente ou vide, lève une EnvironmentError
    avec un message explicite indiquant le nom de la variable manquante,
    sans en exposer la valeur.

    Args:
        key: Nom de la variable d'environnement.

    Returns:
        La valeur de la variable sous forme de chaîne de caractères.

    Raises:
        EnvironmentError: Si la variable est absente ou vide.
    """
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Variable d'environnement requise manquante : '{key}'. "
            f"Vérifiez que le fichier .env est présent à la racine du projet "
            f"et que cette variable y est définie."
        )
    return value


def _get_optional(key: str, default: str) -> str:
    """
    Récupère la valeur d'une variable d'environnement optionnelle.

    Si la variable est absente, retourne la valeur par défaut fournie.

    Args:
        key: Nom de la variable d'environnement.
        default: Valeur retournée si la variable est absente.

    Returns:
        La valeur de la variable, ou la valeur par défaut.
    """
    return os.getenv(key, default)

# Configuration email


def get_imap_folders() -> list[str]:
    """
    Retourne la liste des dossiers IMAP à surveiller.

    Lit la variable IMAP_FOLDERS (liste de dossiers séparés par des virgules).
    Si la variable est absente ou vide, retourne ["INBOX"] par défaut.

    Returns:
        Liste des noms de dossiers IMAP à surveiller.
    """
    raw = os.getenv("IMAP_FOLDERS", "")
    if not raw.strip():
        return [DEFAULT_IMAP_FOLDER]
    return [f.strip() for f in raw.split(",") if f.strip()]


def get_email_config() -> dict:
    """
    Retourne la configuration complète pour la connexion IMAP.

    Returns:
        Dictionnaire contenant les paramètres de connexion email.
    """
    return {
        "imap_server": _get_required("IMAP_SERVER"),
        "imap_port": int(_get_required("IMAP_PORT")),
        "email_address": _get_required("EMAIL_ADDRESS"),
        "email_password": _get_required("EMAIL_PASSWORD"),
        "email_folders": get_imap_folders(),
    }

# Configuration WhatsApp (Green API)


def get_green_api_config() -> dict:
    """
    Retourne la configuration complète pour l'instance Green API WhatsApp.

    Returns:
        Dictionnaire contenant l'identifiant d'instance et le token API.

    Raises:
        EnvironmentError: Si GREENAPI_INSTANCE_ID ou GREENAPI_API_TOKEN
            est absent ou vide dans le fichier .env.
    """
    return {
        "instance_id": _get_required("GREENAPI_INSTANCE_ID"),
        "api_token": _get_required("GREENAPI_API_TOKEN"),
    }

# Configuration des destinataires WhatsApp


def get_whatsapp_groups() -> dict:
    """
    Charge dynamiquement les groupes WhatsApp depuis les variables d'environnement.

    Toute variable dont le nom commence par WHATSAPP_GROUP_ est incluse.
    La clé du dictionnaire retourné est le suffixe en minuscules :
    WHATSAPP_GROUP_URGENT → "urgent", WHATSAPP_GROUP_MON_EQUIPE → "mon_equipe".

    Les variables dont la valeur est vide ou ne contient que des espaces
    ne produisent pas d'entrée dans le dictionnaire.

    Returns:
        Dictionnaire associant chaque nom de groupe à son identifiant chatId WhatsApp.

    Raises:
        EnvironmentError: Si aucune variable WHATSAPP_GROUP_* n'est définie ou
            toutes ont une valeur vide.
    """
    groups = {}
    for key, value in os.environ.items():
        if key.startswith(_WHATSAPP_GROUP_PREFIX):
            stripped = value.strip()
            if stripped:
                suffix = key[len(_WHATSAPP_GROUP_PREFIX):]
                groups[suffix.lower()] = stripped
    if not groups:
        raise EnvironmentError(
            "Aucun groupe WhatsApp configuré. Définissez au moins une variable "
            "d'environnement suivant la convention WHATSAPP_GROUP_<NOM>=<chatId>. "
            "Exemple : WHATSAPP_GROUP_URGENT=120363000000000001@g.us"
        )
    return groups

# Configuration des logs


def get_log_config() -> dict:
    """
    Retourne la configuration du système de logs.

    Returns:
        Dictionnaire contenant le niveau de log et le chemin du fichier.
    """
    return {
        "log_level": _get_optional("LOG_LEVEL", "INFO"),
        "log_file": _get_optional("LOG_FILE", "logs/audit.log"),
    }

# Règles de routage


def get_routing_rules() -> dict:
    """
    Charge et retourne les règles de routage depuis config/routing_rules.yaml.

    Returns:
        Dictionnaire contenant la liste des règles et la cible de repli.

    Raises:
        FileNotFoundError: Si le fichier routing_rules.yaml est introuvable.
    """
    rules_file = _PROJECT_ROOT / "config" / "routing_rules.yaml"
    if not rules_file.exists():
        raise FileNotFoundError(
            f"Fichier de règles de routage introuvable : '{rules_file}'"
        )
    with rules_file.open(encoding="utf-8") as f:
        return yaml.safe_load(f)

# Filtres de mots-clés


def get_filters() -> dict:
    """
    Retourne la configuration des filtres de mots-clés depuis routing_rules.yaml.

    Le bloc 'filters' est optionnel. S'il est absent, les deux listes
    sont vides et tous les emails sont traités.

    Returns:
        Dictionnaire avec les clés 'include' et 'exclude', chacune contenant
        une liste de chaînes de caractères (peut être vide).
    """
    rules = get_routing_rules()
    raw = rules.get("filters") or {}
    return {
        "include": raw.get("include") or [],
        "exclude": raw.get("exclude") or [],
    }


# Configuration générale de l'application


def get_app_config() -> dict:
    """
    Retourne la configuration générale de l'application.

    Returns:
        Dictionnaire contenant l'environnement d'exécution et
        l'intervalle de polling.
    """
    return {
        "app_env": _get_optional("APP_ENV", "production"),
        "polling_interval": int(
            _get_optional("POLLING_INTERVAL_SECONDS", "10")
        ),
    }
