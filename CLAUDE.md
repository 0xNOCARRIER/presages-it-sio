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
- **Main initiale** :
  - 4 joueurs → 5 cartes chacun
  - 5 joueurs → 5 cartes pour l'équipe de 3, 4 cartes pour l'équipe de 2
  - 6 joueurs → 4 cartes chacun
- **Objectif** : être le premier joueur (dans son équipe) à n'avoir plus qu'**une seule carte** en main.
- **Égalité** : si plusieurs joueurs finissent un tour avec 1 carte, celui dont la carte restante a la **valeur la plus haute** donne la victoire à son équipe.
- **La Chance (13)** : si un joueur arrive à 0 carte grâce à La Chance, il bat les joueurs à 1 carte.
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
| ROUGE | 22 | LA JALOUSIE | ⚡ Échangez CETTE CARTE avec une autre carte DÉJÀ EN JEU |
| ROUGE | 23 | L'ORGUEIL | La personne située à votre gauche commence le prochain tour |
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
- **Le Miroir annule La Tristesse** : si les deux sont en jeu, `ignore_highest` est annulé.
- **La Chance ne peut pas défausser La Peur** : la carte `unbreakable` est exclue de la chaîne.
- **La Loi (contrainte)** : annulée si la carte est renvoyée en main via La Colère ou La Trahison.
- **L'Orgueil (22→23)** : la carte est à la valeur 23 en rouge. La Jalousie est à la valeur 22. Cette correction a eu lieu suite à la détection d'une inversion dans le deck.

## Fonctionnalités implémentées

### Comptes et sessions
- Inscription / connexion par identifiant + mot de passe
- Sessions via cookie (30 jours)
- Historique des parties stocké par joueur (SQLite, persistant entre redémarrages)
- Classement global (`/api/leaderboard`) avec ratio victoires/parties

### Salons multijoueur
- Création de salon → code à 6 caractères à partager
- Option de minuterie de tour (10, 15 ou 20 secondes) choisie avant la création du salon
- WebSockets pour communication temps réel
- Chat intégré dans le salon
- Démarrage à 4, 5 ou 6 joueurs

### Logique de jeu
- Deck de 35 cartes correctes
- Distribution selon regles.md : manche 1 = 1 Absolu face visible + cartes, équipes formées ensuite ; manche 2+ = Absolus actifs remélangés avec réguliers (les Absolus non utilisés — 2 ou 1 selon le nb de joueurs — sont définitivement écartés)
- Formation automatique des équipes via Absolus (min + max = même équipe)
- `active_absolu_ids` : liste des IDs d'Absolus réellement utilisés dans la partie
- Résolution des effets ⚡ immédiats et ⏳ de fin de pli
- Overlay d'interaction pour effets à choix
- Condition de victoire : 1 carte en main (ou 0 via La Chance), égalité par valeur max
- Match en 2 manches gagnantes
- `manche_winner_pid` : joueur qui ouvre la manche suivante (gagnant de la manche précédente)

### Minuterie de tour (sablier)
- Par défaut **10 secondes** par joueur ; configurable à 10, 15 ou 20 s avant création du salon
- `room.turn_timer_seconds` stocké dans `GameRoom`
- À l'expiration, une carte valide est auto-jouée aléatoirement (contrainte Loi respectée si possible)
- Message WS `turn_timer {pid, seconds}` envoyé au client dès que c'est le tour d'un humain
- Sablier animé côté frontend dans l'indicateur de tour
- Les bots n'ont pas de minuterie (ils jouent via `run_bots()`)

### Fermeture automatique pour inactivité
- Monitor asyncio lancé au démarrage : vérifie toutes les 10 s
- Si un salon non-lobby n'a aucune activité WS depuis **30 secondes**, il est fermé
- `room.last_activity_at` mis à jour à chaque message WebSocket reçu

### Interface
- **Deux thèmes** : sombre (défaut) et clair, toggle via bouton ☀/🌙 en haut à droite, persisté en `localStorage`
- **Échelle globale** adaptée au thème
- Cartes **165×240px**
- Indicateur de tour animé (pulse quand c'est à toi) + **sablier ⏳Xs** avec barre de progression
- Bannière animée au gagnant du pli + cartes gagnantes qui brillent, perdantes qui s'estompent
- **`trick_review`** : overlay avec statuts ★/✕/↩, messages d'effets, bouton "Continuer ▶" (hôte)
- **Effets interactifs** : barre `#action-bar` au-dessus de la main ; éléments du plateau `.int-target` cliquables
- **La Loi** : deux gros boutons flèches ▼ (<15) et ▲ (>15), avec description visuelle de la contrainte
- **Statistiques joueur** affichées sur l'écran d'accueil (victoires / parties)
- **Fin de manche** : `#roundend-panel` centré, non plein-écran

### Code admin (dev)
- Un **code admin unique** généré au premier démarrage, stocké dans `app_config` (clé `admin_join_code`)
- Format : `ADMIN-XXXXXXXX`, persisté, affiché dans les logs au démarrage
- Exposé via constante Python `ADMIN_JOIN_CODE`
- **Aucune logique de salon/admin n'est branchée** pour l'instant

### Mode développeur (solo)
- Endpoint `POST /api/rooms/dev` crée un salon avec 3 bots : **Arcana**, **Sibyl**, **Morrigan**
- Démarrage immédiat (pas besoin d'attendre 4 humains)
- IA simple : `bot_choose_card()` score les cartes en fonction de leur probabilité d'être défaussées
- `run_bots()` : coroutine asyncio, délai de **0,9 s** entre chaque carte posée par un bot
- Badge 🤖 DEV visible dans le lobby, icône 🤖 sur les joueurs bots

## Points techniques / décisions importantes

### Backend
- `_play_card_logic` gère à la fois les joueurs humains et les bots.
- `card["_owner"]` : champ injecté au moment du jeu, utilisé par Le Rêve pour retrouver la main d'origine quand la carte est dans un slot ≠ son propriétaire.
- `_cancel_turn_timer(room)` : synchrone, annule la task asyncio stockée dans `room._turn_timer_task`.
- `_start_turn_timer(room)` : async, démarre le minuteur pour le prochain humain ; no-op si bot ou état non "playing".
- `_inactivity_monitor()` : tâche infinie lancée dans `lifespan`, ferme les rooms inactives (state ≠ "lobby" et `last_activity_at` > 30 s).
- Le backend expose un état `public_state` complet avec l'état de pli + review time + `turn_timer_seconds`.
- Action WebSocket `continue_trick` (réservée à l'hôte) pour passer le trick_review.
- Nginx **DOIT** avoir `proxy_read_timeout 86400` sinon les WebSockets se coupent après quelques minutes.
- La DB SQLite est créée au démarrage si absente (pas de migration séparée). Les stats sont persistées automatiquement.

### Frontend
- `S.timerSeconds` : minuterie sélectionnée avant création du salon (passée au POST /api/rooms comme `{timer_seconds: N}`)
- `_timerInterval` / `_timerPid` / `_timerSecs` : état du sablier JS côté client
- Le message WS `turn_timer` déclenche le countdown ; tout nouveau `state` efface le sablier
- Thème stocké dans `localStorage("presages_theme")`, appliqué via `data-theme` sur `<html>`
- La Loi : l'overlay montre 2 boutons géants (▼ <15 et ▲ >15) ; la contrainte s'applique côté backend

## Bugs résolus (historique)

1. **Nombre de cartes erroné** → refait avec les 35 cartes officielles nommées.
2. **Main de 7 cartes au lieu de 5** → corrigé.
3. **Absolus mal colorés** → maintenant BLEU, ce qui impacte Hiver/Amitié/etc.
4. **Cartes illisibles** → taille portée à 165×240.
5. **Tour trop rapide / pas de feedback** → ajout de l'état `trick_review`.
6. **Bug de La Loi (et autres effets interactifs)** : la condition `not room.dev_mode` bloquait à tort l'overlay en partie normale. Corrigé.
7. **Race condition** entre `send_state` et `send_to` sur `interaction_required` → résolu via l'état `trick_review` et un ordre d'envoi corrigé.
8. **Jalousie/Orgueil inversés** : Jalousie était à 23, Orgueil à 22. Corrigé (Jalousie=22, Orgueil=23).
9. **Absolus non utilisés réinjectés en manche 2** → corrigés via `active_absolu_ids`, seuls les N Absolus tirés en manche 1 restent actifs.
10. **La Chance défaussait La Peur** → corrigé, `unbreakable` exclu de la chaîne.
11. **Le Miroir n'annulait pas La Tristesse** → corrigé, `ignore_highest = False` si `lowest_wins` aussi.
12. **La Loi (contrainte) persistait après renvoi en main** → annulée via Colère et Trahison.
13. **0 carte (La Chance) ne gagnait pas la manche** → corrigé dans `check_win_condition`.
14. **Manche 2+ ouverte par le mauvais joueur** → `manche_winner_pid` stocké et utilisé.
15. **Le Rêve sans réponse de la cible** → implémenté : cible humaine reçoit `interaction_required (reve_response)` et choisit une carte.

## Déploiement sur Debian 12

### Résumé des étapes

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx
sudo mkdir -p /opt/presages && sudo chown $USER:$USER /opt/presages
# transférer main.py, index.html, requirements.txt dans /opt/presages/
cd /opt/presages && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000  # test manuel
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

### Nginx

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

### HTTPS & pare-feu

```bash
sudo certbot --nginx -d ton-domaine.com
sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw reload
```

## Commandes utiles

```bash
sudo journalctl -u presages -f
sudo systemctl restart presages
sudo systemctl status presages
```

## Points d'attention pour la prochaine session

- **Ne pas inventer de cartes** : le deck est figé à 35 cartes listées ci-dessus.
- **Respecter 4-6 joueurs** : pas de mode 2 ou 3 joueurs.
- **Vérifier `proxy_read_timeout`** si un utilisateur signale des déconnexions.
- Si un effet interactif ne déclenche pas d'overlay, vérifier la condition dans `_play_card_logic` (ancien bug `not room.dev_mode`).
- Le mode dev doit **toujours** rester fonctionnel pour le debug solo.
- La minuterie de tour ne démarre que pour les joueurs humains (`nxt.startswith("bot_")` → pas de timer).
- `CreateRoomBody` requiert un body JSON `{timer_seconds: 10|15|20}` pour `POST /api/rooms` ; le frontend l'envoie toujours via `createRoom()`.
- La DB SQLite survit aux redémarrages du serveur (les stats sont bien persistantes).
