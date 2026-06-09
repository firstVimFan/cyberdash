#!/usr/bin/env python3
"""
CyberDash – Tableau de bord de veille cybersécurité pour terminal.
Lance une boucle infinie : récupère les flux, affiche le dashboard, attend 2h, répète.
Compatible avec la supervision externe (systemd timer) : détecte les mises à jour du cache.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Ajouter le répertoire du projet au path pour les imports locaux
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich import box
from rich.align import Align
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from config import (
    CACHE_FILE,
    DATA_DIR,
    MAX_DISPLAY_CRITICAL,
    MAX_DISPLAY_CYBERSEC,
    MAX_DISPLAY_IT,
    REFRESH_INTERVAL,
)
from fetcher import fetch_all_feeds, load_cache

# ── Logging ───────────────────────────────────────────────────────────────────
DATA_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(DATA_DIR / "cyberdash.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cyberdash.dashboard")

console = Console(highlight=False)

# ── Signaux ───────────────────────────────────────────────────────────────────

def _signal_handler(sig, _frame):
    console.print("\n[bold yellow]  CyberDash arrêté.[/bold yellow]\n")
    sys.exit(0)

signal.signal(signal.SIGINT,  _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# ── Formatage ─────────────────────────────────────────────────────────────────

def _trunc(text: str, maxlen: int) -> str:
    return (text[:maxlen - 1] + "…") if len(text) > maxlen else text


def _time_ago(iso_date: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_date)
        diff = datetime.now(timezone.utc) - dt
        total = int(diff.total_seconds())
        if total < 0:
            return "à l'instant"
        h, rem = divmod(total, 3600)
        m = rem // 60
        if h > 0:
            return f"{h}h{m:02d}"
        return f"{m}m"
    except Exception:
        return "?"


def _local_dt(iso_date: Optional[str]) -> str:
    if not iso_date:
        return "jamais"
    try:
        dt = datetime.fromisoformat(iso_date).astimezone()
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_date


# ── Sections d'affichage ──────────────────────────────────────────────────────

def _render_header(data: Dict) -> None:
    last_update = data.get("last_update")
    stats       = data.get("stats", {})
    errors      = data.get("fetch_errors", [])

    # Ligne de titre
    title = Text()
    title.append("  ⚡  CYBERSECURITY INTELLIGENCE DASHBOARD  ⚡  ", style="bold bright_cyan")

    # Ligne de stats
    stats_line = Text()
    stats_line.append("  Articles : ",    style="dim")
    stats_line.append(str(stats.get("total", 0)),    style="bold white")
    stats_line.append("   Critiques : ", style="dim")
    stats_line.append(str(stats.get("critical", 0)), style="bold red")
    stats_line.append("   Nouveaux : ",  style="dim")
    stats_line.append(str(stats.get("new_this_fetch", 0)), style="bold green")
    stats_line.append("   Prochain rafraîchissement : ", style="dim")
    stats_line.append("dans ~2h", style="bold yellow")
    if errors:
        stats_line.append("   ⚠ Sources en erreur : ", style="dim red")
        stats_line.append(str(len(errors)), style="bold red")

    # Ligne d'horodatage
    ts_line = Text(f"  Dernière MAJ : {_local_dt(last_update)}", style="dim cyan")

    header_content = Text.assemble(title, "\n", stats_line, "\n", ts_line)

    console.print(
        Panel(header_content, border_style="bright_cyan", box=box.DOUBLE_EDGE, padding=(0, 1)),
        "\n",
    )


def _article_card(art: Dict, accent: str) -> None:
    """
    Affiche un article sur 3 lignes :
      1. âge + source    (coloré, discret)
      2. ❯ titre         (bright_white gras)
      3.   URL           (texte BRUT sans ANSI — xfce4-terminal détecte
                          automatiquement les URLs http:// et les rend
                          Ctrl+cliquables via son matcher intégré)
    """
    age    = _time_ago(art.get("published", ""))
    source = art["source"]
    title  = _trunc(art["title"], 160)
    url    = art["url"]

    # Ligne meta : âge · source
    meta = Text()
    meta.append(f"  {age:>5}  ·  ", style=f"bold {accent}")
    meta.append(source,              style=accent)
    console.print(meta)

    # Titre gras
    title_line = Text()
    title_line.append("  ❯ ", style=f"bold {accent}")
    title_line.append(title,  style="bold bright_white")
    console.print(title_line)

    # URL en texte BRUT — zéro code ANSI, zéro OSC 8.
    # Les codes couleur cassent le regex URL de xfce4-terminal.
    # Avec du texte pur : Ctrl+Clic ouvre directement dans le navigateur.
    sys.stdout.write(f"    {url}\n")
    sys.stdout.flush()


def _render_section(
    articles: List[Dict],
    icon: str,
    label: str,
    accent: str,
    max_count: int,
) -> None:
    items     = articles[:max_count]
    n         = len(items)
    count_str = f"{n} alerte{'s' if n > 1 else ''}" if n else "aucune"

    console.print()
    console.print(Rule(f"{icon}  {label}  ·  {count_str}", style=f"bold {accent}"))
    console.print()

    if not items:
        console.print(Padding(f"[dim]  Rien à signaler dans les 48 dernières heures.[/dim]", (0, 4)))
        console.print()
        return

    sep = Text("  " + "╌" * min(60, max(20, (console.width or 100) - 4)), style=f"dim {accent}")

    for i, art in enumerate(items):
        _article_card(art, accent)
        if i < n - 1:
            console.print(sep)

    console.print()


def _render_critical(articles: List[Dict]) -> None:
    _render_section(articles, "🔥", "MENACES CRITIQUES", "red",    MAX_DISPLAY_CRITICAL)


def _render_cybersec(articles: List[Dict]) -> None:
    _render_section(articles, "⚠️ ", "CYBER ACTUALITÉS", "yellow", MAX_DISPLAY_CYBERSEC)


def _render_it(articles: List[Dict]) -> None:
    _render_section(articles, "💻", "IT ACTUALITÉS",     "blue",   MAX_DISPLAY_IT)


def _render_footer(errors: List[str]) -> None:
    if errors:
        console.print(Rule(style="dim red"))
        console.print(Text(
            f"  Sources en erreur (ignorées) : {', '.join(errors)}",
            style="dim red",
        ))
    console.print(Rule(style="dim cyan"))
    console.print(Text(
        "  Ctrl+C quitter  │  Ctrl+Clic URL = ouvrir  │  Sélectionner+Copier = copier l'URL  │  Refresh 2h  │  14 sources",
        style="dim",
    ))
    console.print()


# ── Rendu complet ─────────────────────────────────────────────────────────────

def render_dashboard(data: Dict) -> None:
    """Efface l'écran et affiche le dashboard complet."""
    console.clear()

    articles = data.get("articles", [])
    errors   = data.get("fetch_errors", [])

    # Partition des catégories (seuls les articles cybersec peuvent être critiques)
    critical = [a for a in articles if a.get("critical") and a.get("type") == "cybersec"]
    cybersec = [a for a in articles if not a.get("critical") and a.get("type") == "cybersec"]
    it_news  = [a for a in articles if a.get("type") == "it"]

    _render_header(data)
    _render_critical(critical)
    _render_cybersec(cybersec)
    _render_it(it_news)
    _render_footer(errors)


# ── Splash screen de démarrage ────────────────────────────────────────────────

def _splash() -> None:
    console.clear()
    logo = Text(justify="center")
    logo.append("\n")
    logo.append("  ██████╗██╗   ██╗██████╗ ███████╗██████╗ ██████╗  █████╗ ███████╗██╗  ██╗\n", style="bright_cyan")
    logo.append(" ██╔════╝╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██║  ██║\n", style="cyan")
    logo.append(" ██║      ╚████╔╝ ██████╔╝█████╗  ██████╔╝██║  ██║███████║███████╗███████║\n", style="bright_cyan")
    logo.append(" ██║       ╚██╔╝  ██╔══██╗██╔══╝  ██╔══██╗██║  ██║██╔══██║╚════██║██╔══██║\n", style="cyan")
    logo.append(" ╚██████╗   ██║   ██████╔╝███████╗██║  ██║██████╔╝██║  ██║███████║██║  ██║\n", style="bright_cyan")
    logo.append("  ╚═════╝   ╚═╝   ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝\n", style="cyan")
    logo.append("\n")
    logo.append("          ⚡  Cybersecurity Intelligence Dashboard  ⚡\n", style="bold bright_cyan")
    logo.append("              Récupération des flux RSS en cours...\n", style="dim")

    console.print(Align.center(logo))


# ── Boucle principale ─────────────────────────────────────────────────────────

def _cache_mtime() -> float:
    try:
        return CACHE_FILE.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def main() -> None:
    """
    Boucle principale :
    1. Récupère les flux (ou charge le cache si récent).
    2. Affiche le dashboard.
    3. Toutes les 30 secondes, vérifie si le cache a été mis à jour
       par un processus externe (systemd timer).
    4. Après REFRESH_INTERVAL secondes, force une nouvelle récupération.
    """
    _splash()
    time.sleep(1)

    data: Optional[Dict] = None
    last_fetch_ts: float = 0.0
    last_cache_mtime: float = _cache_mtime()

    while True:
        now = time.time()
        should_fetch = (now - last_fetch_ts) >= REFRESH_INTERVAL

        if should_fetch:
            try:
                console.clear()
                console.print("[dim cyan]  Récupération des flux RSS…[/dim cyan]")
                data = fetch_all_feeds()
                last_fetch_ts    = time.time()
                last_cache_mtime = _cache_mtime()
                logger.info("Récupération complète : %d articles", len(data.get("articles", [])))
            except Exception as exc:
                logger.error("Échec fetch_all_feeds : %s", exc)
                # Fallback sur le cache
                if data is None:
                    cached = load_cache()
                    if cached.get("articles"):
                        data = cached
                        data.setdefault("fetch_errors", []).append("[mode cache]")
                    else:
                        console.print(f"[bold red]  Erreur et cache vide : {exc}[/bold red]")
                        console.print("[dim]  Nouvelle tentative dans 5 minutes…[/dim]")
                        time.sleep(300)
                        continue

        render_dashboard(data)

        # Boucle d'attente avec détection de mise à jour externe du cache
        elapsed = 0
        while elapsed < REFRESH_INTERVAL:
            time.sleep(30)
            elapsed += 30

            current_mtime = _cache_mtime()
            if current_mtime != last_cache_mtime:
                # Cache mis à jour par le timer systemd → on recharge et réaffiche
                fresh = load_cache()
                if fresh.get("articles"):
                    data = fresh
                    last_cache_mtime = current_mtime
                    logger.info("Cache externe détecté, réaffichage")
                    render_dashboard(data)


if __name__ == "__main__":
    # Mode silencieux pour le timer systemd : fetch sans interface graphique
    if "--fetch-only" in sys.argv:
        logging.getLogger("cyberdash").info("Lancement en mode fetch-only (systemd timer)")
        fetch_all_feeds()
        sys.exit(0)
    main()
