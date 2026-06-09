"""
CyberDash – Moteur de récupération RSS.
Gère : requêtes HTTP avec timeout et retry, parsing feedparser,
cache JSON local, déduplication, filtrage temporel, détection critique.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import feedparser
import requests
from dateutil import parser as dateparser

from config import (
    CACHE_FILE,
    CRITICAL_KEYWORDS,
    DATA_DIR,
    FEEDS,
    HOURS_LIMIT,
    LOG_FILE,
    MAX_ARTICLES_PER_FEED,
    MAX_RETRIES,
    NETWORK_TIMEOUT,
    USER_AGENT,
)

# ── Logging ───────────────────────────────────────────────────────────────────
DATA_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cyberdash.fetcher")

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
})


# ── Utilitaires ───────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    text = _HTML_TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _article_id(url: str, title: str) -> str:
    """Identifiant stable pour la déduplication."""
    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:20]


def _parse_date(entry) -> Optional[datetime]:
    """Extrait la date de publication en UTC depuis une entrée feedparser."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime.fromtimestamp(calendar.timegm(val), tz=timezone.utc)
            except Exception:
                pass

    for attr in ("published", "updated", "created"):
        val = getattr(entry, attr, None)
        if val:
            try:
                dt = dateparser.parse(val)
                if dt:
                    return dt.astimezone(timezone.utc)
            except Exception:
                pass

    return None


def _is_critical(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(kw.lower() in text for kw in CRITICAL_KEYWORDS)


def _sanity_check_date(dt: Optional[datetime]) -> Optional[datetime]:
    """Rejette les dates absurdes (futur > 1h ou trop vieilles)."""
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    if dt > now + timedelta(hours=1):
        return now
    return dt


# ── Récupération d'un flux ────────────────────────────────────────────────────

def _fetch_one(feed_cfg: Dict) -> Tuple[List[Dict], Optional[str]]:
    """
    Récupère et parse un flux RSS/Atom.
    Retourne (articles, message_erreur_ou_None).
    """
    url  = feed_cfg["url"]
    name = feed_cfg["name"]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_LIMIT)

    last_error: Optional[str] = None

    for attempt in range(MAX_RETRIES):
        try:
            resp = _SESSION.get(url, timeout=NETWORK_TIMEOUT)
            resp.raise_for_status()

            feed = feedparser.parse(resp.content)

            if feed.bozo and not feed.entries:
                raise ValueError(f"feedparser bozo: {feed.bozo_exception}")

            articles: List[Dict] = []
            for entry in feed.entries[:MAX_ARTICLES_PER_FEED * 2]:
                title   = _strip_html(getattr(entry, "title",   "") or "")
                link    = getattr(entry, "link", "").strip()
                summary_raw = (
                    getattr(entry, "summary", "")
                    or getattr(entry, "description", "")
                    or ""
                )
                summary = _strip_html(summary_raw)[:400]

                if not title or not link:
                    continue

                pub = _sanity_check_date(_parse_date(entry))
                if pub is None:
                    pub = datetime.now(timezone.utc)
                elif pub < cutoff:
                    continue

                articles.append({
                    "id":       _article_id(link, title),
                    "title":    title,
                    "url":      link,
                    "summary":  summary,
                    "source":   name,
                    "type":     feed_cfg["type"],
                    "published": pub.isoformat(),
                    "critical": _is_critical(title, summary),
                })

                if len(articles) >= MAX_ARTICLES_PER_FEED:
                    break

            logger.info("[%s] %d articles récupérés", name, len(articles))
            return articles, None

        except requests.Timeout:
            last_error = "timeout"
            logger.warning("[%s] Timeout (tentative %d/%d)", name, attempt + 1, MAX_RETRIES)
        except requests.HTTPError as exc:
            last_error = f"HTTP {exc.response.status_code}"
            logger.warning("[%s] %s (tentative %d/%d)", name, last_error, attempt + 1, MAX_RETRIES)
        except Exception as exc:
            last_error = str(exc)[:120]
            logger.error("[%s] Erreur: %s", name, last_error)
            break  # Pas de retry sur erreur inconnue

        if attempt < MAX_RETRIES - 1:
            time.sleep(2 ** attempt)  # backoff exponentiel léger

    return [], last_error or "erreur inconnue"


# ── Cache ─────────────────────────────────────────────────────────────────────

def load_cache() -> Dict:
    """Charge le cache JSON depuis le disque. Retourne un dict vide si absent ou corrompu."""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                logger.info("Cache chargé : %d articles", len(data.get("articles", [])))
                return data
    except Exception as exc:
        logger.warning("Échec chargement cache : %s", exc)
    return {"articles": [], "last_update": None, "fetch_errors": [], "stats": {}}


def _save_cache(data: Dict) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        tmp.replace(CACHE_FILE)
        logger.info("Cache sauvegardé : %d articles", len(data.get("articles", [])))
    except Exception as exc:
        logger.error("Échec sauvegarde cache : %s", exc)


# ── Point d'entrée principal ──────────────────────────────────────────────────

def fetch_all_feeds() -> Dict:
    """
    Récupère tous les flux configurés, fusionne avec le cache existant,
    déduplique, filtre les vieux articles, et sauvegarde.
    Retourne le dictionnaire de données complet.
    """
    cache = load_cache()
    known_ids: set = {a["id"] for a in cache.get("articles", [])}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_LIMIT)

    fresh_articles: List[Dict] = []
    errors: List[str] = []

    for feed_cfg in FEEDS:
        arts, err = _fetch_one(feed_cfg)
        fresh_articles.extend(arts)
        if err:
            errors.append(feed_cfg["name"])

    # Fusionner nouveaux + cache (déduplication par ID)
    new_count = 0
    merged_map: Dict[str, Dict] = {}

    for article in fresh_articles:
        if article["id"] not in merged_map:
            merged_map[article["id"]] = article
            if article["id"] not in known_ids:
                new_count += 1

    for article in cache.get("articles", []):
        if article["id"] not in merged_map:
            # Garder seulement si encore dans la fenêtre temporelle
            try:
                pub = datetime.fromisoformat(article["published"])
                if pub >= cutoff:
                    merged_map[article["id"]] = article
            except Exception:
                pass

    # Trier par date décroissante
    all_articles = sorted(
        merged_map.values(),
        key=lambda a: a.get("published", ""),
        reverse=True,
    )

    # Seuls les articles cybersec critiques sont comptés (cohérent avec l'affichage)
    critical_count = sum(1 for a in all_articles if a.get("critical") and a.get("type") == "cybersec")

    result = {
        "articles":     all_articles,
        "last_update":  datetime.now(timezone.utc).isoformat(),
        "fetch_errors": errors,
        "stats": {
            "total":          len(all_articles),
            "critical":       critical_count,
            "new_this_fetch": new_count,
            "sources_failed": len(errors),
        },
    }

    _save_cache(result)
    return result
