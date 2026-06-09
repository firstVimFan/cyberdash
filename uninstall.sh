#!/usr/bin/env bash
# =============================================================================
# CyberDash – Script de désinstallation complète
# Usage : bash uninstall.sh
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
step()    { echo -e "\n${BOLD}${CYAN}▶ $*${RESET}"; }

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
DATA_DIR="$HOME/.local/share/cyberdash"
AUTOSTART_DIR="$HOME/.config/autostart"
SYSTEMD_DIR="$HOME/.config/systemd/user"

echo -e "${RED}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║   CyberDash – Désinstallation        ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${RESET}"

read -rp "  Confirmer la désinstallation complète ? [o/N] " confirm
[[ "$confirm" =~ ^[oOyY]$ ]] || { echo "Annulé."; exit 0; }

# ── Systemd ───────────────────────────────────────────────────────────────────
step "Arrêt et désactivation du timer systemd"
if systemctl --user is-enabled cyberdash-fetch.timer &>/dev/null; then
    systemctl --user disable --now cyberdash-fetch.timer 2>/dev/null && success "Timer désactivé"
else
    warn "Timer non actif (ignoré)"
fi
rm -f "$SYSTEMD_DIR/cyberdash-fetch.service" "$SYSTEMD_DIR/cyberdash-fetch.timer"
systemctl --user daemon-reload 2>/dev/null || true
success "Unités systemd supprimées"

# ── Autostart XDG ─────────────────────────────────────────────────────────────
step "Suppression de l'entrée autostart XDG"
rm -f "$AUTOSTART_DIR/cyberdash.desktop"
success "Fichier autostart supprimé"

# ── Scripts wrapper ───────────────────────────────────────────────────────────
step "Suppression des scripts exécutables"
rm -f "$BIN_DIR/cyberdash" "$BIN_DIR/cyberdash-fetch" "$BIN_DIR/cyberdash-launch"
success "Scripts supprimés"

# ── Virtualenv ────────────────────────────────────────────────────────────────
step "Suppression du virtualenv Python"
if [ -d "$INSTALL_DIR/.venv" ]; then
    rm -rf "$INSTALL_DIR/.venv"
    success "Virtualenv supprimé"
else
    warn "Virtualenv non trouvé"
fi

# ── Données / cache / logs ────────────────────────────────────────────────────
step "Suppression des données (cache et logs)"
read -rp "  Supprimer aussi le cache et les logs ? ($DATA_DIR) [o/N] " rm_data
if [[ "$rm_data" =~ ^[oOyY]$ ]]; then
    rm -rf "$DATA_DIR"
    success "Données supprimées"
else
    info "Données conservées : $DATA_DIR"
fi

# ── Nettoyage PATH ────────────────────────────────────────────────────────────
step "Nettoyage du PATH dans les fichiers shell"
for rcfile in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rcfile" ] && grep -q "CyberDash" "$rcfile"; then
        # Supprimer les 2 lignes ajoutées par install.sh
        grep -v "CyberDash" "$rcfile" | grep -v 'export PATH="$HOME/.local/bin:$PATH"' > "$rcfile.tmp" || true
        mv "$rcfile.tmp" "$rcfile"
        info "PATH nettoyé dans $rcfile"
    fi
done

echo ""
echo -e "${GREEN}  ✅  CyberDash désinstallé proprement.${RESET}"
echo "  Les fichiers sources ($INSTALL_DIR) n'ont pas été touchés."
echo ""
