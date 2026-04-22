# Présages — Jeu de cartes multijoueur auto-hébergé

## Contexte et objectif

Implémentation web du jeu de société **Présages** (jeu de cartes français) pour auto-hébergement sur serveur personnel. Multijoueur en ligne en temps réel, comptes utilisateurs, historique des parties, style visuel sobre et ésotérique.

## Stack technique

- **Backend** : Python 3.10+ / FastAPI / WebSockets
- **Base de données** : SQLite (comptes, sessions, historique)
- **Frontend** : HTML + JS vanilla dans un fichier unique (pas de framework)
- **Auth** : cookies de session
- **Déploiement cible** : Debian 12 + Nginx (reverse proxy) + systemd + HTTPS via Certbot

## Architecture des fichiers

```
/opt/presages/
├── main.py           # Serveur FastAPI : logique de jeu, WS, auth, SQLite
├── index.html        # Client unique (sobre, thème ésotérique/mystique)
├── requirements.txt  # Dépendances Python
└── README.md         # Guide de déploiement
```

**Principe** : un seul fichier HTML servi statiquement, toute la logique jeu côté serveur, communication par WebSockets.

## Règles du jeu (officielles, à respecter strictement)

- **Nombre de joueurs** : 4, 5 ou 6 **uniquement** (pas 2 ni 3)
- **Équipes** :
  - 4 joueurs → 2v2
  - 5 joueurs → 2v3
  - 6 joueurs → 2v2v2
- **Formation des équipes** : automatique via les cartes L'Absolu (valeurs 30-35). Le joueur avec la plus grande valeur d'Absolu et celui avec la plus petite forment une équipe, etc.
- **Main** : **5 cartes par joueur** (1 Absolu + 4 cartes piochées)
- **Objectif** : être le premier joueur (dans son équipe) à n'avoir plus qu'**une seule carte** en main.
- **Égalité** : si plusieurs joueurs finissent un tour avec 1 carte, celui dont la carte restante a la **valeur la plus haute** donne la victoire à son équipe.
- **Partie** : se gagne en **2 manches**.

### Déroulement d'un tour (pli)

1. Le gagnant du pli précédent commence (sauf effet contraire, cf. L'Orgueil).
2. Chaque joueur pose une carte face visible devant lui, dans le sens horaire.
3. Si la carte posée a un effet **⚡ (foudre / immédiat)**, il se résout tout de suite, avant que le joueur suivant joue.
4. Quand tout le monde a posé, tous les effets **⏳ (sablier / fin de pli)** se résolvent simultanément.
5. Le pli est remporté par la carte de plus forte valeur (sauf effet contraire, ex : Le Miroir).
6. La carte gagnante est défaussée. Les cartes dont un effet demande la défausse le sont aussi. Les autres retournent en main.

## Deck complet — 35 cartes

| Couleur | Valeur | Nom | Effet |
|---|---|---|---|
| VERT | 1 | LA VIE | Défaussez la carte VERTE de plus FORTE valeur |
| VERT | 2 | L'AMOUR | Défaussez cette carte si au moins UNE AUTRE carte VERTE est en jeu |
| VERT | 3 | L'AMITIÉ | Défaussez cette carte si au moins une carte JAUNE est en jeu |
| VERT | 4 | LE CALME | Défaussez cette carte si au moins une carte ROUGE est en jeu |
| VERT | 5 | LE FESTIN | Défaussez cette carte si au moins une carte BLEUE est en jeu |
| VERT | 6 | L'ESPOIR | Défaussez cette carte si ELLE EST la carte de plus FAIBLE valeur en jeu |
| VERT | 7 | LE PRINTEMPS | Défaussez cette carte si c'est la SEULE carte VERTE en jeu |
| VERT | 8 | LA MORT | Défaussez la carte VERTE de plus FAIBLE valeur |
| JAUNE | 9 | LE MENSONGE | Défaussez la carte JAUNE de plus FORTE valeur |
| JAUNE | 10 | L'ÉNIGME | Défaussez cette carte si au moins une carte L'ABSOLU (30-35) est en jeu |
| JAUNE | 11 | L'ÉTÉ | Défaussez cette carte si c'est la SEULE carte JAUNE en jeu |
| JAUNE | 12 | LA PEUR | Cette carte ne PEUT PAS être défaussée, sauf si elle remporte le tour |
| JAUNE | 13 | LA CHANCE | Si cette carte est défaussée, défaussez-vous d'une carte de votre main |
| JAUNE | 14 | LE MIROIR | La carte de plus FAIBLE valeur remporte le tour |
| JAUNE | 15 | LA LOI | ⚡ Les joueurs qui n'ont pas encore joué doivent, si possible, jouer une carte plus FAIBLE ou plus FORTE que 15 (vous choisissez) |
| JAUNE | 16 | LA VÉRITÉ | Défaussez la carte JAUNE de plus FAIBLE valeur |
| TOUTES | 17 | LA MALICE | Cette carte est de toutes les couleurs |
| ROUGE | 18 | LE JOUR | Défaussez la carte ROUGE de plus FORTE valeur |
| ROUGE | 19 | L'AUTOMNE | Défaussez cette carte si c'est la SEULE carte ROUGE en jeu |
| ROUGE | 20 | L'HARMONIE | Défaussez la carte de plus FAIBLE valeur |
| ROUGE | 21 | LE RÊVE | ⚡ Vous POUVEZ jouer cette carte devant une personne qui n'a pas encore joué. Elle doit jouer une carte devant vous |
| ROUGE | 22 | L'ORGUEIL | La personne située à votre gauche commence le prochain tour |
| ROUGE | 23 | LA JALOUSIE | ⚡ Échangez CETTE CARTE avec une autre carte DÉJÀ EN JEU |
| ROUGE | 24 | LE SECRET | ⚡ La personne de votre choix vous montre une carte OU montrez une carte à la personne de votre choix |
| ROUGE | 25 | LA NUIT | Défaussez la carte ROUGE de plus FAIBLE valeur |
| BLEU | 26 | LA TRISTESSE | La VALEUR de la carte la plus forte est IGNORÉE |
| BLEU | 27 | L'HIVER | Défaussez TOUTES les cartes JAUNES en jeu |
| BLEU | 28 | LA COLÈRE | ⚡ Renvoyez dans sa main une carte se trouvant devant une autre personne. Elle doit jouer UNE AUTRE carte |
| BLEU | 29 | LA TRAHISON | ⚡ Échangez une carte de VOTRE MAIN avec une carte DÉJÀ EN JEU |
| BLEU | 30-35 | L'ABSOLU (×6) | ⚡ Échangez une carte de VOTRE MAIN avec la personne de votre choix |

### Notes importantes sur les effets

- **Les 6 Absolus sont de couleur BLEUE** (impact sur L'Hiver, L'Amitié, etc.).
- **Effets ⚡ (immédiats)** : La Loi, Le Rêve, La Jalousie, Le Secret, La Colère, La Trahison, L'Absolu — résolus **dès la pose de la carte**.
- **Effets interactifs** (nécessitent un choix du joueur) : La Loi (choix faible/fort), Le Rêve (cible), La Jalousie (carte cible), Le Secret (cible + montrer/voir), La Colère (cible + nouvelle carte), La Trahison (carte propre + cible), L'Absolu (cible).
- **Tous les effets sont implémentés intégralement**, pas de version simplifiée.

## Fonctionnalités implémentées

### Comptes et sessions
- Inscription / connexion par identifiant + mot de passe
- Sessions via cookie
- Historique des parties stocké par joueur (SQLite)

### Salons multijoueur
- Création de salon → code à 6 caractères à partager
- WebSockets pour communication temps réel
- Chat intégré dans le salon
- Démarrage à 4, 5 ou 6 joueurs

### Logique de jeu
- Deck de 35 cartes correctes
- Distribution : 1 Absolu + 4 cartes piochées (main de 5)
- Formation automatique des équipes via Absolus
- Résolution des effets ⚡ immédiats et ⏳ de fin de pli
- Overlay d'interaction pour effets à choix
- Condition de victoire : 1 carte en main, égalité par valeur max
- Match en 2 manches gagnantes

### Interface
- **Échelle globale ×1.5** : root font-size à 24px (au lieu de 16px), tous les rem sont agrandis proportionnellement.
- Cartes **165×240px** (pip 18px, padding 9px).
- Panels agrandis : auth 570px, home 600px, teams 270px, chat 345px, colonne droite lobby 450px.
- Indicateur de tour animé (pulse quand c'est à toi) — **taille 2.4rem en pulse** ("✦ À vous de jouer !" rendu bien visible), 1.2rem sinon.
- Bannière animée au gagnant du pli + cartes gagnantes qui brillent, perdantes qui s'estompent
- **Pas de popups/overlays pendant le jeu** — tout se passe sur le plateau :
  - **`trick_review`** : bande `#trick-banner` sous le plateau, badges ★/✕/↩ sur les cartes, bouton "Continuer ▶" (hôte uniquement)
  - **Effets interactifs** : barre `#action-bar` au-dessus de la main ; les éléments du plateau (.int-target) s'illuminent et sont cliquables (ombres joueurs, cartes jouées, main)
  - **Le Secret (main révélée)** : affiché dans le chat (onglet Messages)
  - **Fin de manche** : `#roundend-panel` centré sur le plateau (position:absolute dans #table-panel), non plein-écran

### Code admin (dev)
- Un **code admin unique** est généré au premier démarrage et stocké dans la table `app_config` (clé `admin_join_code`).
- Format : `ADMIN-XXXXXXXX` (8 caractères hex), persisté — le même code est réutilisé à chaque redémarrage.
- **Affiché dans les logs** au démarrage : `[Présages] Code admin (dev) : ADMIN-XXXXXXXX`.
- Exposé en mémoire via la constante Python `ADMIN_JOIN_CODE` (dans `main.py`).
- **Pour l'instant, aucune logique de salon/admin n'est branchée** — le code est juste créé et persisté. La logique de rejoindre une partie en admin / debug / administration sera ajoutée plus tard.

### Mode développeur (solo)
- Endpoint `POST /api/rooms/dev` crée un salon avec 3 bots : **Arcana**, **Sibyl**, **Morrigan**
- Démarrage immédiat possible (pas besoin d'attendre 4 humains)
- IA simple : `bot_choose_card()` score les cartes en fonction de leur probabilité d'être défaussées et de leurs effets
- `run_bots()` : coroutine asyncio, délai de **0,9 s** entre chaque carte posée par un bot
- `_resolve_and_advance()` : logique de résolution mutualisée humain/bot
- Le bouton "Terminer le pli" fonctionne aussi en mode dev
- Badge 🤖 DEV visible dans le lobby, icône 🤖 sur les joueurs bots

## Points techniques / décisions importantes

- `_play_card_logic` gère à la fois les joueurs humains et les bots.
- Le backend expose un état `public_state` complet avec l'état de pli + review time.
- Action WebSocket `continue_trick` (réservée à l'hôte) pour valider la review et passer au pli suivant.
- Nginx **DOIT** avoir `proxy_read_timeout 86400` sinon les WebSockets se coupent après quelques minutes.
- La DB SQLite est créée au démarrage si absente (pas de migration séparée).

## Bugs résolus (historique)

1. **Nombre de cartes erroné** → refait avec les 35 cartes officielles nommées.
2. **Main de 7 cartes au lieu de 5** → corrigé.
3. **Absolus mal colorés** → maintenant BLEU, ce qui impacte Hiver/Amitié/etc.
4. **Cartes illisibles** → taille portée à 110×160 avec polices plus grandes.
5. **Tour trop rapide / pas de feedback** → ajout de l'état `trick_review` avec bouton "Continuer ▶" (hôte uniquement, pas de décompte automatique).
6. **Bug de La Loi (et autres effets interactifs)** : la condition `not room.dev_mode` dans le backend bloquait à tort l'ouverture de l'overlay d'interaction **même en partie normale**. Corrigé.
7. **Race condition** entre `send_state` et `send_to` sur `interaction_required` → résolu via le nouvel état `trick_review` et un ordre d'envoi corrigé.

## Déploiement sur Debian 12

### Résumé des étapes

```bash
# 1. Dépendances système
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx

# 2. Dossier projet
sudo mkdir -p /opt/presages
sudo chown $USER:$USER /opt/presages
# -> transférer main.py, index.html, requirements.txt, README.md dans /opt/presages/

# 3. Venv Python
cd /opt/presages
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Test manuel
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Service systemd

`/etc/systemd/system/presages.service` :

```ini
[Unit]
Description=Présages Game Server
After=network.target

[Service]
User=ton_user
WorkingDirectory=/opt/presages
ExecStart=/opt/presages/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now presages
```

### Nginx reverse proxy

`/etc/nginx/sites-available/presages` :

```nginx
server {
    listen 80;
    server_name ton-domaine.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;  # CRITIQUE pour les WebSockets
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/presages /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d ton-domaine.com
```

### Pare-feu

```bash
sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw reload
```

## Commandes utiles

```bash
# Logs en direct
sudo journalctl -u presages -f

# Redémarrer après mise à jour de main.py ou index.html
sudo systemctl restart presages

# Statut
sudo systemctl status presages
```

## TODO / pistes d'amélioration possibles

- Améliorer l'IA des bots (actuellement très simple : score basé sur défausse probable).
- Ajouter un système de reconnexion après coupure WebSocket.
- Sauvegarder l'état de partie pour permettre la reprise après crash serveur.
- Animations plus riches (poses de cartes, échanges).
- Statistiques par joueur au-delà du simple historique.
- Tests automatisés de la logique des effets (particulièrement les interactifs).
- Internationalisation (tout est en français).

## Points d'attention pour la prochaine session

- **Ne pas inventer de cartes** : le deck est figé à 35 cartes listées ci-dessus.
- **Respecter 4-6 joueurs** : pas de mode 2 ou 3 joueurs.
- **Vérifier `proxy_read_timeout`** si un utilisateur signale des déconnexions.
- Si un effet interactif ne déclenche pas d'overlay, vérifier d'abord la condition dans `_play_card_logic` (ancien bug `not room.dev_mode`).
- Le mode dev doit **toujours** rester fonctionnel pour le debug solo.
