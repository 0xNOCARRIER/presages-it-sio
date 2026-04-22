# ✦ Présages — Auto-hébergement

Jeu de cartes en équipe pour 4 à 6 joueurs, basé sur la mécanique de défausse de Présages (Spiral Editions).

## Prérequis

- Python 3.10+
- pip

## Installation

```bash
# Cloner / copier les fichiers dans un dossier
cd presages/

# Installer les dépendances
pip install -r requirements.txt
```

## Lancement

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Puis ouvrir : **http://localhost:8000**

## Exposition sur Internet

### Option 1 — Reverse proxy Nginx (recommandé)

```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

> Pour HTTPS : `certbot --nginx -d votre-domaine.com`

### Option 2 — Accès direct (dev/test)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Ouvrir le port 8000 dans votre pare-feu / box.

### Option 3 — systemd (service permanent)

```ini
# /etc/systemd/system/presages.service
[Unit]
Description=Présages Game Server
After=network.target

[Service]
WorkingDirectory=/opt/presages
ExecStart=/usr/local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure
User=www-data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable presages
sudo systemctl start presages
```

## Structure des fichiers

```
presages/
├── main.py           ← Serveur FastAPI (logique de jeu + WebSockets + auth)
├── index.html        ← Interface cliente (un seul fichier)
├── requirements.txt  ← Dépendances Python
├── presages.db       ← Base SQLite (créée automatiquement au premier lancement)
└── README.md
```

## Base de données

SQLite locale (`presages.db`), créée automatiquement.  
Tables : `users` (comptes), `game_history` (historique des parties).

## Règles implémentées

- Configuration 4 / 5 / 6 joueurs
- Formation automatique des équipes par cartes L'Absolu (plus haute + plus basse = même équipe)
- Effets des cartes : ⏳ sablier (fin de tour) + ⚡ foudre (immédiat)
- Tous les effets : color_match, highest_color, lowest_color, lone_color, unbreakable, chain, lowest_wins
- Victoire en 2 manches
- Chat en temps réel
- Historique des parties par joueur

## Interface

Toutes les actions se déroulent directement sur le plateau de jeu, sans popup ni fenêtre modale :

- **Résultat du pli** : affiché en bande sous le plateau (badges ★/✕/↩ sur les cartes)
- **Effets interactifs** (La Jalousie, La Colère, La Trahison, Le Rêve, L'Absolu, La Loi, Le Secret) : une barre contextuelle apparaît au-dessus de la main ; les éléments du plateau (cartes adverses, ombres de joueurs, cartes en main) s'illuminent et deviennent cliquables directement
- **Main révélée** (Le Secret) : affichée dans le chat
- **Fin de manche** : panneau centré sur le plateau, non plein-écran
- **Carte jouée** par le joueur local affichée juste au-dessus de sa main
- **Joueur dont c'est le tour** : ombre entourée d'or avec indicateur ▶ clignotant
- **Nombre de cartes** affiché en badge doré à côté des mini-cartes de chaque ombre
- **Panel équipes** (colonne gauche) agrandi et plus lisible ; bouton **Quitter la partie** en bas
- **Reprendre une partie en cours** : si vous quittez une partie puis revenez au menu, un bouton "Reprendre" apparaît automatiquement avec le code du salon
