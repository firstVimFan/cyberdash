#!/usr/bin/env bash
# =============================================================================
# CyberDash – Script d'installation automatique
# Testé sur Kali Linux (XFCE). Compatible Debian/Ubuntu avec ajustements.
# Usage : bash install.sh
# =============================================================================
set -euo pipefail

# ── Couleurs ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERREUR]${RESET} $*" >&2; exit 1; }
step()    { echo -e "\n${BOLD}${CYAN}▶ $*${RESET}"; }

# ── Chemins ───────────────────────────────────────────────────────────────────
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$INSTALL_DIR/.venv"
DATA_DIR="$HOME/.local/share/cyberdash"
BIN_DIR="$HOME/.local/bin"
AUTOSTART_DIR="$HOME/.config/autostart"
SYSTEMD_DIR="$HOME/.config/systemd/user"
WRAPPER_SCRIPT="$BIN_DIR/cyberdash"
LAUNCHER_SCRIPT="$BIN_DIR/cyberdash-launch"

# ── Bannière ──────────────────────────────────────────────────────────────────
echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║   CyberDash – Installation                        ║"
echo "  ║   Tableau de bord de veille cybersécurité         ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo -e "${RESET}"
info "Répertoire d'installation : $INSTALL_DIR"

# ── 1. Dépendances système ────────────────────────────────────────────────────
step "Vérification des dépendances système"

if ! command -v python3 &>/dev/null; then
    error "python3 introuvable. Installez-le avec : sudo apt install python3"
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PYTHON_VER détecté"
if python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"; then
    success "Version Python compatible (≥ 3.8)"
else
    error "Python 3.8+ requis (détecté : $PYTHON_VER)"
fi

# Installer python3-venv si absent
if ! python3 -c "import venv" &>/dev/null; then
    info "Installation de python3-venv…"
    sudo apt-get install -y python3-venv python3-pip 2>/dev/null \
        || warn "Impossible d'installer python3-venv via apt. Essai pip direct."
fi

# ── 2. Environnement virtuel Python ──────────────────────────────────────────
step "Création de l'environnement virtuel Python"

if [ -d "$VENV_DIR" ]; then
    warn "Virtualenv existant trouvé – réinstallation des dépendances"
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR"
success "Virtualenv créé : $VENV_DIR"

"$VENV_DIR/bin/pip" install --upgrade pip --quiet
info "Installation des dépendances Python…"
"$VENV_DIR/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"
success "Dépendances Python installées"

# ── 3. Répertoire de données ──────────────────────────────────────────────────
step "Création du répertoire de données"
mkdir -p "$DATA_DIR"
success "Répertoire de données : $DATA_DIR"

# ── 4. Scripts wrapper ────────────────────────────────────────────────────────
step "Création des scripts exécutables"
mkdir -p "$BIN_DIR"

# Wrapper principal (lance le dashboard dans le venv)
cat > "$WRAPPER_SCRIPT" << WRAPPER_EOF
#!/usr/bin/env bash
# CyberDash – exécuteur principal
exec "$VENV_DIR/bin/python3" "$INSTALL_DIR/dashboard.py" "\$@"
WRAPPER_EOF
chmod +x "$WRAPPER_SCRIPT"
success "Script principal : $WRAPPER_SCRIPT"

# Wrapper de fetch seul (pour le timer systemd)
FETCH_SCRIPT="$BIN_DIR/cyberdash-fetch"
cat > "$FETCH_SCRIPT" << FETCH_EOF
#!/usr/bin/env bash
# CyberDash – mise à jour du cache RSS uniquement (sans affichage)
exec "$VENV_DIR/bin/python3" "$INSTALL_DIR/dashboard.py" --fetch-only
FETCH_EOF
chmod +x "$FETCH_SCRIPT"
success "Script fetch-only : $FETCH_SCRIPT"

# ── 5. Détection de l'émulateur de terminal ───────────────────────────────────
step "Détection de l'émulateur de terminal"

detect_terminal() {
    for term in xfce4-terminal xterm qterminal gnome-terminal konsole lxterminal; do
        if command -v "$term" &>/dev/null; then
            echo "$term"
            return
        fi
    done
    echo "xterm"  # fallback garanti sur tout système X
}

TERM_EMULATOR=$(detect_terminal)
info "Émulateur détecté : $TERM_EMULATOR"

# Construire la commande de lancement selon l'émulateur
case "$TERM_EMULATOR" in
    xfce4-terminal)
        TERM_CMD="$TERM_EMULATOR --title='CyberDash' --geometry=220x60 --hide-menubar -e '$WRAPPER_SCRIPT'"
        ;;
    xterm)
        TERM_CMD="$TERM_EMULATOR -title 'CyberDash' -geometry 220x60 -fa 'Monospace' -fs 10 -e '$WRAPPER_SCRIPT'"
        ;;
    qterminal)
        TERM_CMD="$TERM_EMULATOR -e '$WRAPPER_SCRIPT'"
        ;;
    gnome-terminal)
        TERM_CMD="$TERM_EMULATOR --title='CyberDash' --geometry=220x60 -- '$WRAPPER_SCRIPT'"
        ;;
    konsole)
        TERM_CMD="$TERM_EMULATOR --title 'CyberDash' -e '$WRAPPER_SCRIPT'"
        ;;
    *)
        TERM_CMD="xterm -title 'CyberDash' -geometry 220x60 -e '$WRAPPER_SCRIPT'"
        ;;
esac

# Launcher script multi-terminal avec fallback automatique
cat > "$LAUNCHER_SCRIPT" << LAUNCHER_EOF
#!/usr/bin/env bash
# CyberDash – lanceur de terminal avec fallback automatique.
# Essaie plusieurs émulateurs dans l'ordre.

WRAPPER="$WRAPPER_SCRIPT"

launch_with() {
    local term="\$1"
    shift
    if command -v "\$term" &>/dev/null; then
        exec "\$term" "\$@" "\$WRAPPER"
        exit 0
    fi
}

case "\$(basename \$(command -v xfce4-terminal xterm qterminal gnome-terminal konsole lxterminal 2>/dev/null | head -1))" in
    xfce4-terminal) exec xfce4-terminal --title='CyberDash' --geometry=220x60 --hide-menubar -e "\$WRAPPER" ;;
    gnome-terminal) exec gnome-terminal --title='CyberDash' --geometry=220x60 -- "\$WRAPPER" ;;
    konsole)        exec konsole --title 'CyberDash' -e "\$WRAPPER" ;;
    qterminal)      exec qterminal -e "\$WRAPPER" ;;
    *)              exec xterm -title 'CyberDash' -geometry 220x60 -fa 'Monospace' -fs 10 -e "\$WRAPPER" ;;
esac
LAUNCHER_EOF
chmod +x "$LAUNCHER_SCRIPT"
success "Launcher : $LAUNCHER_SCRIPT"

# ── 6. XDG Autostart ─────────────────────────────────────────────────────────
step "Configuration de l'autostart XDG (lancement à la connexion graphique)"
mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/cyberdash.desktop" << DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=CyberDash
GenericName=Cybersecurity Dashboard
Comment=Tableau de bord de veille cybersécurité – lance automatiquement au login
Exec=$LAUNCHER_SCRIPT
Icon=utilities-terminal
Terminal=false
Categories=Network;Security;
Keywords=security;cybersecurity;dashboard;news;
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
StartupNotify=false
DESKTOP_EOF

success "Fichier autostart : $AUTOSTART_DIR/cyberdash.desktop"

# ── 7. Services systemd utilisateur ──────────────────────────────────────────
step "Installation des unités systemd utilisateur (rafraîchissement en arrière-plan)"
mkdir -p "$SYSTEMD_DIR"

# Service de mise à jour du cache RSS
cat > "$SYSTEMD_DIR/cyberdash-fetch.service" << SERVICE_EOF
[Unit]
Description=CyberDash – Mise à jour du cache RSS
Documentation=file://$INSTALL_DIR/README
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=$FETCH_SCRIPT
StandardOutput=journal
StandardError=journal
# Sécurité minimale pour un service utilisateur
PrivateTmp=true
NoNewPrivileges=true
SERVICE_EOF

# Timer : 2 minutes après le boot, puis toutes les 2 heures
cat > "$SYSTEMD_DIR/cyberdash-fetch.timer" << TIMER_EOF
[Unit]
Description=CyberDash – Timer de rafraîchissement RSS (2h)
Requires=cyberdash-fetch.service

[Timer]
OnBootSec=2min
OnUnitActiveSec=2h
RandomizedDelaySec=60
AccuracySec=1min
Unit=cyberdash-fetch.service
Persistent=true

[Install]
WantedBy=timers.target
TIMER_EOF

# Rechargement et activation
systemctl --user daemon-reload 2>/dev/null || warn "Impossible de recharger systemd (normal hors session graphique)"

if systemctl --user enable --now cyberdash-fetch.timer 2>/dev/null; then
    success "Timer systemd activé : cyberdash-fetch.timer"
else
    warn "Timer systemd non activé (normal en mode headless). À activer manuellement :"
    warn "  systemctl --user enable --now cyberdash-fetch.timer"
fi

# ── 8. Vérification de PATH ───────────────────────────────────────────────────
step "Vérification du PATH utilisateur"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "$BIN_DIR absent du PATH."
    info "Ajout automatique dans ~/.bashrc et ~/.zshrc"
    for rcfile in "$HOME/.bashrc" "$HOME/.zshrc"; do
        if [ -f "$rcfile" ]; then
            if ! grep -q "$BIN_DIR" "$rcfile"; then
                echo "" >> "$rcfile"
                echo "# CyberDash" >> "$rcfile"
                echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$rcfile"
                info "$BIN_DIR ajouté à $rcfile"
            fi
        fi
    done
fi

# ── 9. Récupération initiale des flux ─────────────────────────────────────────
step "Récupération initiale des flux RSS (peut prendre 30 à 60 secondes…)"
"$FETCH_SCRIPT" && success "Cache initial créé" || warn "Certains flux ont échoué (vérifiez la connexion réseau)"

# ── Résumé ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}║  ✅  CyberDash installé avec succès !                     ║${RESET}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${RESET}"
echo -e "${GREEN}║${RESET}  Commandes utiles :                                       ${GREEN}║${RESET}"
echo -e "${GREEN}║${RESET}    cyberdash              → lancer le dashboard           ${GREEN}║${RESET}"
echo -e "${GREEN}║${RESET}    cyberdash-fetch         → mettre à jour le cache RSS   ${GREEN}║${RESET}"
echo -e "${GREEN}║${RESET}    cyberdash-launch        → ouvrir un terminal + dashboard${GREEN}║${RESET}"
echo -e "${GREEN}║${RESET}                                                           ${GREEN}║${RESET}"
echo -e "${GREEN}║${RESET}  Fichiers :                                               ${GREEN}║${RESET}"
echo -e "${GREEN}║${RESET}    Cache     : $DATA_DIR/cache.json  ${GREEN}║${RESET}"
echo -e "${GREEN}║${RESET}    Logs      : $DATA_DIR/cyberdash.log${GREEN}║${RESET}"
echo -e "${GREEN}║${RESET}                                                           ${GREEN}║${RESET}"
echo -e "${GREEN}║${RESET}  Le terminal s'ouvrira automatiquement à la prochaine     ${GREEN}║${RESET}"
echo -e "${GREEN}║${RESET}  connexion graphique (XDG Autostart).                     ${GREEN}║${RESET}"
echo -e "${GREEN}║${RESET}  Pour désinstaller : bash uninstall.sh                    ${GREEN}║${RESET}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${RESET}"
echo ""
info "Pour lancer immédiatement : cyberdash-launch"
