# Système de notification automatique

## Avant de commencer

Vérifiez que vous disposez des éléments suivants avant de démarrer
l'installation.

**Sur votre ordinateur :**
- Windows 10 ou 11
- Python 3.12 — téléchargeable sur [python.org](https://www.python.org/downloads/)
  (cochez « Add Python to PATH » lors de l'installation)

**Comptes et accès :**
- Un compte Gmail dédié à la réception des alertes, avec un
  **mot de passe d'application** généré (différent du mot de passe habituel —
  voir section Configuration)
- Un compte Green API avec une instance WhatsApp liée via QR code —
  créez un compte sur [green-api.com](https://green-api.com/en) si vous n'en avez
  pas encore un
- Les groupes WhatsApp destinataires avec le téléphone lié à Green API ajouté
  comme participant

---

## Installation

Ces étapes ne sont à réaliser qu'une seule fois.

**1. Ouvrez PowerShell** en tant qu'utilisateur normal (pas besoin
d'administrateur).

**2. Placez-vous dans le dossier du programme :**
```powershell
cd "C:\chemin\vers\notification-system"
```
Remplacez le chemin par l'emplacement réel du dossier sur votre machine.

**3. Créez l'espace de travail Python isolé :**
```powershell
py -3.12 -m venv venv
```

**4. Activez cet espace de travail :**
```powershell
.\venv\Scripts\Activate.ps1
```
Si PowerShell affiche une erreur de politique d'exécution, lancez d'abord
cette commande puis recommencez l'étape 4 :
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**5. Installez les dépendances :**
```powershell
pip install -r requirements.txt
```

**6. Créez votre fichier de configuration :**
```powershell
copy .env.example .env
```

Passez maintenant à la section **Configuration** pour remplir ce fichier.

---

## Configuration

### Étape 1 — Remplir le fichier `.env`

Ouvrez le fichier `.env` avec le Bloc-notes ou tout éditeur de texte.
Remplacez chaque valeur fictive par votre valeur réelle en vous aidant
du tableau ci-dessous.

**Connexion à la boîte email**

| Paramètre | Ce qu'il faut mettre |
|---|---|
| `IMAP_SERVER` | `imap.gmail.com` pour Gmail — ne pas modifier |
| `IMAP_PORT` | `993` — ne pas modifier |
| `EMAIL_ADDRESS` | Adresse Gmail utilisée pour la réception des alertes |
| `EMAIL_PASSWORD` | Mot de passe d'application Gmail (voir ci-dessous) |
| `IMAP_FOLDERS` | Dossiers à surveiller — laisser `INBOX` pour la boîte de réception principale. Pour surveiller plusieurs dossiers, séparez-les par des virgules : `INBOX,Alertes` |

> **Comment obtenir un mot de passe d'application Gmail :**
> Connectez-vous au compte Gmail concerné → Compte Google → Sécurité →
> Vérification en deux étapes (à activer si ce n'est pas fait) →
> Mots de passe des applications → créez-en un pour « Autre application »
> et nommez-le « OCP Notification ». Copiez le code à 16 caractères affiché.

**Connexion WhatsApp (Green API)**

| Paramètre | Ce qu'il faut mettre |
|---|---|
| `GREENAPI_INSTANCE_ID` | Numéro d'instance visible sur le dashboard green-api.com (format : `1101XXXXXX`) |
| `GREENAPI_API_TOKEN` | Jeton d'accès visible sur le dashboard, sous le numéro d'instance |

> L'instance Green API doit être en statut **Online** (liée via QR code)
> pour que les envois fonctionnent. Si elle est hors ligne, le programme
> affiche un avertissement au démarrage mais continue de tourner — les
> notifications seront envoyées dès que l'instance sera reconnectée.

**Groupes WhatsApp destinataires**

Chaque groupe cible est déclaré sur une ligne séparée. Le nom que vous
choisissez après `WHATSAPP_GROUP_` doit correspondre exactement (en
minuscules) à la valeur `target:` dans le fichier de règles
`config/routing_rules.yaml`.

Exemple :
```
WHATSAPP_GROUP_URGENT=120363000000000001@g.us
WHATSAPP_GROUP_MAINTENANCE=120363000000000002@g.us
WHATSAPP_GROUP_GENERAL=120363000000000003@g.us
```

Pour trouver les identifiants de vos groupes WhatsApp, consultez la
section **Trouver les identifiants de groupes** ci-dessous.

**Autres paramètres (optionnels)**

| Paramètre | Description | Valeur par défaut |
|---|---|---|
| `POLLING_INTERVAL_SECONDS` | Fréquence de vérification de la boîte mail, en secondes | `10` |
| `LOG_LEVEL` | Niveau de détail du fichier de trace (`INFO` ou `DEBUG`) | `INFO` |
| `LOG_FILE` | Emplacement du fichier de trace | `logs/audit.log` |

---

### Étape 2 — Configurer les règles de routage

Ouvrez le fichier `config/routing_rules.yaml` avec le Bloc-notes.

Ce fichier définit quels mots-clés dans un email déclenchent une
notification vers quel groupe WhatsApp. Voici un exemple de règle :

```yaml
- name: urgent_alert
  description: "Alertes critiques"
  keywords:
      - "urgent"
      - "panne"
      - "alarme"
  target: urgent
  priority: 1
```

- **`keywords`** : liste de mots-clés à rechercher dans le sujet et le corps
  de l'email (insensible à la casse)
- **`target`** : nom du groupe destinataire — doit correspondre au suffixe
  d'une variable `WHATSAPP_GROUP_<NOM>` dans votre fichier `.env`
- **`priority`** : ordre d'évaluation des règles (1 = évaluée en premier)

La ligne `fallback_target: general` en bas du fichier définit le groupe
par défaut si aucune règle ne correspond à un message.

**Filtres optionnels**

Vous pouvez ignorer certains emails ou n'en traiter qu'une partie en
ajoutant un bloc `filters:` à la fin du fichier :

```yaml
filters:
  include:
    - pompe
    - alarme
  exclude:
    - test
    - spam
```

- `include` : seuls les emails contenant au moins un de ces mots sont traités
- `exclude` : les emails contenant un de ces mots sont ignorés

Sans ce bloc, tous les emails reçus sont traités.

---

### Étape 3 — Trouver les identifiants de vos groupes WhatsApp

Les identifiants de groupes WhatsApp ont un format particulier
(`1203XXXXXXXXXX@g.us`). Un script est fourni pour les récupérer
automatiquement depuis votre compte Green API.

Dans PowerShell, depuis le dossier du programme (avec l'espace de travail
activé) :

```powershell
.\scripts\Get-WhatsAppGroups.ps1
```

Le script vous demande votre identifiant d'instance et votre jeton Green API,
puis affiche la liste de vos groupes WhatsApp avec leurs identifiants. Il
génère également le bloc prêt à coller dans votre fichier `.env`.

---

## Utilisation au quotidien

**Lancer le programme :**

```powershell
# Si l'espace de travail n'est pas encore activé dans cette fenêtre :
.\venv\Scripts\Activate.ps1

# Démarrer le programme :
python main.py
```

Au démarrage, le programme affiche les dossiers surveillés et les filtres
actifs, vérifie que l'instance WhatsApp est en ligne, puis commence le
polling.

**Commandes disponibles pendant l'exécution :**

| Touche | Action |
|---|---|
| `P` | Mettre en pause / reprendre la surveillance |
| `Q` | Arrêter proprement le programme |
| `Ctrl+C` | Arrêter proprement le programme |

Le programme fonctionne en arrière-plan tant que la fenêtre PowerShell reste
ouverte. Fermez la fenêtre ou appuyez sur `Q` pour l'arrêter.
