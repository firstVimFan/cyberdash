# CyberDash ⚡

Tableau de bord de veille cybersécurité et IT pour terminal, conçu pour Kali Linux.  
S'ouvre automatiquement à la connexion graphique, se rafraîchit toutes les 2 heures sans intervention.

```
╔══════════════════════════════════════════════════════════════════════╗
║   ⚡  CYBERSECURITY INTELLIGENCE DASHBOARD  ⚡                       ║
║   Articles : 124   Critiques : 27   Nouveaux : 8   Prochain : ~2h   ║
║   Dernière MAJ : 2026-06-09 18:24:19                                 ║
╚══════════════════════════════════════════════════════════════════════╝

🔥  MENACES CRITIQUES
 Âge    Titre                                              Source           Lien
 ─────────────────────────────────────────────────────────────────────────────
 9m     New Veeam vulnerability exposes backup servers…   BleepingComputer https://…
 49m    Russian Attackers Weaponize WinRAR Flaw…          Dark Reading     https://…
 1h58   SAP Patches Critical NetWeaver Vulnerabilities    SecurityWeek     https://…

⚠️   CYBER ACTUALITÉS
 …

💻   IT ACTUALITÉS
 …
```

---

## Fonctionnalités

- **3 sections** : Menaces critiques (rouge) · Cyber actualités (jaune) · IT actualités (bleu)
- **Détection automatique** des articles critiques par mots-clés (CVE, ransomware, RCE, APT…)
- **14 sources RSS** fiables, toutes vérifiées et fonctionnelles
- **Filtre 48h** : seuls les articles récents sont affichés
- **Déduplication** : aucun doublon entre les sources
- **Cache local JSON** : fonctionne même si le réseau est temporairement indisponible
- **Retry automatique** avec backoff sur chaque source défaillante
- **Rafraîchissement double** : boucle interne 2h + timer systemd en arrière-plan
- **Lancement automatique** au démarrage de la session graphique (XDG Autostart)

---

## Sources RSS

### Cybersécurité (10 flux)

| Source | Contenu |
|--------|---------|
| The Hacker News | Actualités cyber généralistes |
| BleepingComputer | Vulnérabilités, malwares, incidents |
| Dark Reading | Threat intelligence, analyses |
| SecurityWeek | CVE, patches, industrie |
| CERT/CC | Vulnérabilités coordonnées |
| Microsoft Security Blog | Bulletins Microsoft |
| Google Security Blog | Recherche Google / Project Zero |
| CrowdStrike Blog | Threat intelligence, APT |
| Palo Alto Unit 42 | Analyses de menaces avancées |
| SANS ISC | Alertes journalières, IoCs |

### IT généraliste (4 flux)

| Source | Contenu |
|--------|---------|
| Ars Technica | Tech, science, sécurité |
| TechCrunch | Startups, industrie tech |
| The Verge | Produits, entreprises tech |
| Wired | Tendances technologiques |

---

## Prérequis

- Kali Linux (ou Debian/Ubuntu) avec session graphique (XFCE recommandé)
- Python 3.8 ou supérieur
- Connexion Internet
- Un émulateur de terminal : `xfce4-terminal`, `xterm`, `qterminal` ou `gnome-terminal`

---

## Installation

### Méthode rapide (recommandée)

```bash
git clone <url-du-repo> ~/cyberdash
cd ~/cyberdash
bash install.sh
```

Ou si vous avez copié les fichiers manuellement :

```bash
cd /chemin/vers/les/fichiers
bash install.sh
```

Le script fait tout automatiquement :

1. Vérifie Python 3.8+
2. Crée un virtualenv Python isolé (`.venv/`)
3. Installe les dépendances (`feedparser`, `requests`, `python-dateutil`, `rich`)
4. Crée le répertoire de données `~/.local/share/cyberdash/`
5. Génère les scripts exécutables dans `~/.local/bin/`
6. Détecte votre émulateur de terminal
7. Configure le **lancement automatique au login** (XDG Autostart)
8. Configure le **timer systemd** pour les mises à jour en arrière-plan
9. Effectue un premier fetch des flux RSS

### Installation manuelle des dépendances

Si vous préférez ne pas utiliser de virtualenv :

```bash
pip3 install feedparser requests python-dateutil rich
```

---

## Lancement au démarrage

CyberDash utilise **deux mécanismes complémentaires** pour le démarrage automatique.

### 1. XDG Autostart (lancement du terminal)

À chaque connexion graphique, un fichier `.desktop` déclenche l'ouverture d'un terminal avec le dashboard.

**Fichier créé par `install.sh` :**

```
~/.config/autostart/cyberdash.desktop
```

**Contenu :**

```ini
[Desktop Entry]
Type=Application
Name=CyberDash
Comment=Tableau de bord de veille cybersécurité
Exec=/home/<user>/.local/bin/cyberdash-launch
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
```

> Le délai de 5 secondes laisse le temps à la session graphique de s'initialiser.

Pour activer/désactiver sans désinstaller :

```bash
# Désactiver
sed -i 's/X-GNOME-Autostart-enabled=true/X-GNOME-Autostart-enabled=false/' \
    ~/.config/autostart/cyberdash.desktop

# Réactiver
sed -i 's/X-GNOME-Autostart-enabled=false/X-GNOME-Autostart-enabled=true/' \
    ~/.config/autostart/cyberdash.desktop
```

### 2. Systemd user timer (mise à jour en arrière-plan)

Même quand le terminal est fermé, le cache RSS est mis à jour toutes les 2 heures. Quand le terminal se rouvre, il affiche immédiatement les données fraîches.

**Fichiers créés par `install.sh` :**

```
~/.config/systemd/user/cyberdash-fetch.service
~/.config/systemd/user/cyberdash-fetch.timer
```

**Commandes de gestion :**

```bash
# Voir l'état du timer
systemctl --user status cyberdash-fetch.timer

# Voir les logs de mise à jour
journalctl --user -u cyberdash-fetch.service -f

# Forcer une mise à jour immédiate
systemctl --user start cyberdash-fetch.service

# Désactiver le timer
systemctl --user disable --now cyberdash-fetch.timer

# Réactiver le timer
systemctl --user enable --now cyberdash-fetch.timer
```

---

## Utilisation

### Lancer manuellement

```bash
# Ouvrir un terminal avec le dashboard
cyberdash-launch

# Lancer directement dans le terminal courant
cyberdash

# Mettre à jour le cache sans afficher le dashboard
cyberdash-fetch
```

### Raccourcis clavier

| Touche | Action |
|--------|--------|
| `Ctrl+C` | Quitter le dashboard |

### Fichiers importants

| Chemin | Contenu |
|--------|---------|
| `~/.local/share/cyberdash/cache.json` | Cache RSS local |
| `~/.local/share/cyberdash/cyberdash.log` | Logs d'exécution |
| `~/.config/autostart/cyberdash.desktop` | Entrée autostart XDG |
| `~/.config/systemd/user/cyberdash-fetch.timer` | Timer systemd |

### Consulter les logs

```bash
# Logs de l'application
tail -f ~/.local/share/cyberdash/cyberdash.log

# Logs du timer systemd
journalctl --user -u cyberdash-fetch.service --since today
```

---

## Structure du projet

```
.
├── config.py          # Sources RSS, mots-clés critiques, constantes
├── fetcher.py         # Moteur de récupération RSS avec cache et dédup
├── dashboard.py       # Interface terminal Rich + boucle de rafraîchissement
├── requirements.txt   # Dépendances Python
├── install.sh         # Script d'installation automatique
├── uninstall.sh       # Script de désinstallation
└── README.md          # Ce fichier
```

---

## Personnalisation

### Ajouter une source RSS

Éditer `config.py`, section `FEEDS` :

```python
{
    "name": "Nom affiché",
    "url":  "https://exemple.com/feed.xml",
    "type": "cybersec",   # ou "it"
},
```

### Modifier l'intervalle de rafraîchissement

Dans `config.py` :

```python
REFRESH_INTERVAL = 7200  # secondes (7200 = 2 heures)
```

Et pour le timer systemd (`~/.config/systemd/user/cyberdash-fetch.timer`) :

```ini
OnUnitActiveSec=2h   # modifier cette valeur
```

Puis recharger : `systemctl --user daemon-reload`

### Modifier la fenêtre temporelle des articles

```python
HOURS_LIMIT = 48   # ignorer les articles plus vieux que N heures
```

### Ajouter des mots-clés critiques

Dans `config.py`, section `CRITICAL_KEYWORDS` :

```python
"votre-mot-clé",
```

---

## Désinstallation

```bash
bash uninstall.sh
```

Le script supprime :
- Le timer et service systemd
- L'entrée XDG Autostart
- Les scripts dans `~/.local/bin/`
- Le virtualenv `.venv/`
- Optionnellement : le cache et les logs (`~/.local/share/cyberdash/`)

Les fichiers sources du projet ne sont pas touchés.

---

## Dépendances Python

| Package | Version minimale | Rôle |
|---------|-----------------|------|
| `feedparser` | 6.0.11 | Parsing des flux RSS/Atom |
| `requests` | 2.31.0 | Requêtes HTTP avec timeout |
| `python-dateutil` | 2.9.0 | Parsing de dates multi-formats |
| `rich` | 13.7.0 | Interface terminal colorée |

---

## Dépannage

**Le terminal ne s'ouvre pas au login**  
Vérifier que l'autostart est activé :
```bash
cat ~/.config/autostart/cyberdash.desktop | grep Autostart-enabled
# Doit afficher : X-GNOME-Autostart-enabled=true
```

**Aucun article affiché**  
Lancer manuellement une mise à jour et vérifier les logs :
```bash
cyberdash-fetch
tail -20 ~/.local/share/cyberdash/cyberdash.log
```

**Une source RSS est toujours en erreur**  
Vérifier la connectivité réseau vers cette source, puis retirer temporairement l'entrée de `config.py` si le problème persiste.

**Le timer systemd n'est pas actif**  
```bash
systemctl --user enable --now cyberdash-fetch.timer
systemctl --user status cyberdash-fetch.timer
```
