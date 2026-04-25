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

## Gestion des comptes

L'inscription publique est **désactivée**. Seul l'administrateur peut créer des comptes, via le panneau d'administration → onglet **Comptes**.

Le compte admin par défaut (créé au premier démarrage) : `admin` / `presages`.

### Création de compte

Dans l'onglet **Comptes** du panneau admin, tapez un pseudonyme : un mot de passe aléatoire est généré automatiquement. Copiez-le avec le bouton **⎘ Copier** ou régénérez-en un autre avec **↻**. Transmettez le mot de passe au joueur concerné.

### Changer de mot de passe

Chaque joueur peut changer son propre mot de passe via le bouton **Changer mdp** sur l'écran d'accueil (saisie de l'ancien mot de passe requise).

### Sauvegarde des comptes et statistiques

Dans l'onglet **Comptes** du panneau admin :

- **Exporter (JSON)** : télécharge un fichier `presages_backup_YYYY-MM-DD.json` contenant tous les comptes et l'historique des parties.
- **Importer (JSON)** : restaure les comptes et l'historique depuis un fichier exporté précédemment.
- **🗑 Stats** (par joueur dans l'onglet **Utilisateurs**) : supprime l'historique de parties d'un joueur précis.
- **🗑 Réinitialiser les stats** : supprime tout l'historique de parties (les comptes restent intacts).

Pour conserver les données après un `git pull` : exportez avant, puis importez après avoir rechargé le serveur.

## Interface

Toutes les actions se déroulent directement sur le plateau de jeu :

- **Résultat du pli** : barre au-dessus de la main affichant les cartes défaussées avec le nom du joueur qui les a posées et une couronne ♛ sur le gagnant du pli
- **Observation des cartes** : au début de chaque manche, 15 secondes d'observation obligatoires (les cartes sont bloquées, une barre de progression compte à rebours)
- **Effets interactifs** (La Jalousie, La Colère, La Trahison, Le Rêve, L'Absolu, La Loi, Le Secret) : une barre contextuelle apparaît au-dessus de la main ; les éléments du plateau s'illuminent et deviennent cliquables
- **Fin de manche** : panneau centré sur le plateau, non plein-écran
- **Fin de partie** : écran dédié avec l'équipe gagnante et l'équipe perdante (avec les noms des joueurs)
- **Score des équipes** : ● pour chaque manche gagnée, ○ pour chaque manche restante (deux par équipe pour gagner la partie)
- **Tour du joueur** : ombre entourée d'or avec indicateur ▶ + lueur dorée sur les cartes en main
- **Cartes jouées** autour du plateau : joueur gauche → carte à sa droite ; joueur droit → carte à sa gauche ; joueurs du haut → carte en dessous de leur ombre ; joueur local → carte au-dessus de sa main
- **Reprendre une partie en cours** : bouton "Reprendre" automatique à l'écran d'accueil si vous avez quitté une partie
- **Thème clair / sombre** : toggle en haut à droite, persisté localement
