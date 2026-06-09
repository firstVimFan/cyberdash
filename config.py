"""
CyberDash – Configuration centrale.
Toutes les constantes et la liste des flux RSS sont ici.
"""
from pathlib import Path

# ── Répertoires ──────────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR    = Path.home() / ".local" / "share" / "cyberdash"
CACHE_FILE  = DATA_DIR / "cache.json"
LOG_FILE    = DATA_DIR / "cyberdash.log"
BIN_DIR     = Path.home() / ".local" / "bin"

# ── Réseau ───────────────────────────────────────────────────────────────────
NETWORK_TIMEOUT  = 15   # secondes par requête
MAX_RETRIES      = 2    # tentatives par flux
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
)

# ── Contenu ───────────────────────────────────────────────────────────────────
HOURS_LIMIT           = 48   # ignorer les articles plus vieux que N heures
REFRESH_INTERVAL      = 7200 # intervalle de rafraîchissement en secondes (2h)
MAX_ARTICLES_PER_FEED = 20   # articles retenus par flux
MAX_DISPLAY_CRITICAL  = 8    # alertes affichées section critique
MAX_DISPLAY_CYBERSEC  = 10   # articles affichés section cybersec
MAX_DISPLAY_IT        = 6    # articles affichés section IT

# ── Mots-clés déclenchant la catégorie "Critique" ────────────────────────────
CRITICAL_KEYWORDS = [
    # CVE explicite
    "CVE-",
    # Techniques zero-day
    "zero-day",
    "0-day",
    "actively exploited",
    "actively being exploited",
    "critical vulnerability",
    "critical flaw",
    "critical patch",
    "emergency patch",
    "out-of-band patch",
    # Malware avéré
    "ransomware",
    "backdoor",
    "rootkit",
    "botnet",
    "exploit kit",
    "malware campaign",
    "cyberattack",
    # Acteurs de menace
    "advanced persistent threat",
    "nation-state",
    "threat actor",
    "APT ",           # espace final pour éviter "rapt", "capt"
    # Techniques RCE / escalade
    "remote code execution",
    "unauthenticated rce",
    "privilege escalation",
    "authentication bypass",
    "pre-auth rce",
    # Compromission
    "data breach",
    "supply chain attack",
    "supply chain compromise",
    # Exploitation de masse
    "mass exploitation",
    "widespread exploitation",
    "under active attack",
]

# ── Flux RSS ──────────────────────────────────────────────────────────────────
FEEDS = [
    # ── Cybersécurité ──
    {
        "name": "The Hacker News",
        "url":  "https://feeds.feedburner.com/TheHackersNews",
        "type": "cybersec",
    },
    {
        "name": "BleepingComputer",
        "url":  "https://www.bleepingcomputer.com/feed/",
        "type": "cybersec",
    },
    {
        "name": "Dark Reading",
        "url":  "https://www.darkreading.com/rss.xml",
        "type": "cybersec",
    },
    {
        "name": "SecurityWeek",
        "url":  "https://feeds.feedburner.com/securityweek",
        "type": "cybersec",
    },
    {
        "name": "CERT/CC Vulns",
        "url":  "https://www.kb.cert.org/vulfeed/",
        "type": "cybersec",
    },
    {
        "name": "Microsoft Security",
        "url":  "https://www.microsoft.com/en-us/security/blog/feed/",
        "type": "cybersec",
    },
    {
        "name": "Google Security Blog",
        "url":  "https://security.googleblog.com/feeds/posts/default",
        "type": "cybersec",
    },
    {
        "name": "CrowdStrike Blog",
        "url":  "https://www.crowdstrike.com/blog/feed/",
        "type": "cybersec",
    },
    {
        "name": "Palo Alto Unit 42",
        "url":  "https://unit42.paloaltonetworks.com/feed/",
        "type": "cybersec",
    },
    {
        "name": "SANS ISC",
        "url":  "https://isc.sans.edu/rssfeed_full.xml",
        "type": "cybersec",
    },
    # ── IT Généraliste ──
    {
        "name": "Ars Technica",
        "url":  "https://feeds.arstechnica.com/arstechnica/index",
        "type": "it",
    },
    {
        "name": "TechCrunch",
        "url":  "https://techcrunch.com/feed/",
        "type": "it",
    },
    {
        "name": "The Verge",
        "url":  "https://www.theverge.com/rss/index.xml",
        "type": "it",
    },
    {
        "name": "Wired",
        "url":  "https://www.wired.com/feed/rss",
        "type": "it",
    },
]
