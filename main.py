"""
Présages – Serveur FastAPI + WebSockets
Jeu de cartes en équipe (4-6 joueurs)
Deck officiel 35 cartes, mains de 5 cartes
"""

import asyncio
import hashlib
import json
import random
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────

DB_PATH = "presages.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin      INTEGER NOT NULL DEFAULT 0,
            is_banned     INTEGER NOT NULL DEFAULT 0,
            created_at    INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS game_history (
            id         TEXT PRIMARY KEY,
            player_id  TEXT NOT NULL,
            game_id    TEXT NOT NULL,
            result     TEXT NOT NULL,
            players    TEXT NOT NULL,
            teams      TEXT NOT NULL,
            duration   INTEGER NOT NULL,
            played_at  INTEGER NOT NULL,
            FOREIGN KEY (player_id) REFERENCES users(id)
        );
    """)
    # Migrations : ajouter colonnes si elles n'existent pas encore
    cols = [r[1] for r in db.execute("PRAGMA table_info(users)").fetchall()]
    if "is_admin"  not in cols:
        db.execute("ALTER TABLE users ADD COLUMN is_admin  INTEGER NOT NULL DEFAULT 0")
    if "is_banned" not in cols:
        db.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0")
    db.commit()

    # Compte admin par défaut
    existing = db.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not existing:
        db.execute(
            "INSERT INTO users (id,username,password_hash,is_admin,is_banned,created_at) VALUES (?,?,?,1,0,?)",
            (str(uuid.uuid4()), "admin", hash_pw("presages"), int(time.time()))
        )
        db.commit()
    else:
        # S'assurer que admin est bien admin
        db.execute("UPDATE users SET is_admin=1 WHERE username='admin'")
        db.commit()
    db.close()

# ─────────────────────────────────────────────────────────────────
# DECK OFFICIEL 35 CARTES
# ─────────────────────────────────────────────────────────────────

DECK_DEFINITION = [
    {"id":"v1",  "value":1,  "color":"vert",  "name":"La Vie",       "effect_type":"highest_own",   "effect_param":None,    "is_absolu":False},
    {"id":"v2",  "value":2,  "color":"vert",  "name":"L'Amour",      "effect_type":"if_other_same", "effect_param":None,    "is_absolu":False},
    {"id":"v3",  "value":3,  "color":"vert",  "name":"L'Amitié",     "effect_type":"if_color",      "effect_param":"jaune", "is_absolu":False},
    {"id":"v4",  "value":4,  "color":"vert",  "name":"Le Calme",     "effect_type":"if_color",      "effect_param":"rouge", "is_absolu":False},
    {"id":"v5",  "value":5,  "color":"vert",  "name":"Le Festin",    "effect_type":"if_color",      "effect_param":"bleu",  "is_absolu":False},
    {"id":"v6",  "value":6,  "color":"vert",  "name":"L'Espoir",     "effect_type":"if_lowest",     "effect_param":None,    "is_absolu":False},
    {"id":"v7",  "value":7,  "color":"vert",  "name":"Le Printemps", "effect_type":"if_lone_color", "effect_param":None,    "is_absolu":False},
    {"id":"v8",  "value":8,  "color":"vert",  "name":"La Mort",      "effect_type":"lowest_own",    "effect_param":None,    "is_absolu":False},
    {"id":"j9",  "value":9,  "color":"jaune", "name":"Le Mensonge",  "effect_type":"highest_own",   "effect_param":None,    "is_absolu":False},
    {"id":"j10", "value":10, "color":"jaune", "name":"L'Énigme",     "effect_type":"if_absolu",     "effect_param":None,    "is_absolu":False},
    {"id":"j11", "value":11, "color":"jaune", "name":"L'Été",        "effect_type":"if_lone_color", "effect_param":None,    "is_absolu":False},
    {"id":"j12", "value":12, "color":"jaune", "name":"La Peur",      "effect_type":"unbreakable",   "effect_param":None,    "is_absolu":False},
    {"id":"j13", "value":13, "color":"jaune", "name":"La Chance",    "effect_type":"chain",         "effect_param":None,    "is_absolu":False},
    {"id":"j14", "value":14, "color":"jaune", "name":"Le Miroir",    "effect_type":"lowest_wins",   "effect_param":None,    "is_absolu":False},
    {"id":"j15", "value":15, "color":"jaune", "name":"La Loi",       "effect_type":"loi",           "effect_param":None,    "is_absolu":False},
    {"id":"j16", "value":16, "color":"jaune", "name":"La Vérité",    "effect_type":"lowest_own",    "effect_param":None,    "is_absolu":False},
    {"id":"m17", "value":17, "color":"multi", "name":"La Malice",    "effect_type":"all_colors",    "effect_param":None,    "is_absolu":False},
    {"id":"r18", "value":18, "color":"rouge", "name":"Le Jour",      "effect_type":"highest_own",   "effect_param":None,    "is_absolu":False},
    {"id":"r19", "value":19, "color":"rouge", "name":"L'Automne",    "effect_type":"if_lone_color", "effect_param":None,    "is_absolu":False},
    {"id":"r20", "value":20, "color":"rouge", "name":"L'Harmonie",   "effect_type":"lowest_all",    "effect_param":None,    "is_absolu":False},
    {"id":"r21", "value":21, "color":"rouge", "name":"Le Rêve",      "effect_type":"reve",          "effect_param":None,    "is_absolu":False},
    {"id":"r22", "value":22, "color":"rouge", "name":"La Jalousie",  "effect_type":"jalousie",      "effect_param":None,    "is_absolu":False},
    {"id":"r23", "value":23, "color":"rouge", "name":"L'Orgueil",    "effect_type":"orgueil",       "effect_param":None,    "is_absolu":False},
    {"id":"r24", "value":24, "color":"rouge", "name":"Le Secret",    "effect_type":"secret",        "effect_param":None,    "is_absolu":False},
    {"id":"r25", "value":25, "color":"rouge", "name":"La Nuit",      "effect_type":"lowest_own",    "effect_param":None,    "is_absolu":False},
    {"id":"b26", "value":26, "color":"bleu",  "name":"La Tristesse", "effect_type":"ignore_highest","effect_param":None,    "is_absolu":False},
    {"id":"b27", "value":27, "color":"bleu",  "name":"L'Hiver",      "effect_type":"all_jaune",     "effect_param":None,    "is_absolu":False},
    {"id":"b28", "value":28, "color":"bleu",  "name":"La Colère",    "effect_type":"colere",        "effect_param":None,    "is_absolu":False},
    {"id":"b29", "value":29, "color":"bleu",  "name":"La Trahison",  "effect_type":"trahison",      "effect_param":None,    "is_absolu":False},
    {"id":"a30", "value":30, "color":"bleu",  "name":"L'Absolu",     "effect_type":"absolu",        "effect_param":None,    "is_absolu":True},
    {"id":"a31", "value":31, "color":"bleu",  "name":"L'Absolu",     "effect_type":"absolu",        "effect_param":None,    "is_absolu":True},
    {"id":"a32", "value":32, "color":"bleu",  "name":"L'Absolu",     "effect_type":"absolu",        "effect_param":None,    "is_absolu":True},
    {"id":"a33", "value":33, "color":"bleu",  "name":"L'Absolu",     "effect_type":"absolu",        "effect_param":None,    "is_absolu":True},
    {"id":"a34", "value":34, "color":"bleu",  "name":"L'Absolu",     "effect_type":"absolu",        "effect_param":None,    "is_absolu":True},
    {"id":"a35", "value":35, "color":"bleu",  "name":"L'Absolu",     "effect_type":"absolu",        "effect_param":None,    "is_absolu":True},
]

INTERACTIVE_EFFECTS = {"loi", "reve", "jalousie", "secret", "colere", "trahison", "absolu"}

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def build_deck():
    return [dict(c) for c in DECK_DEFINITION]

def effective_colors(card):
    if card["effect_type"] == "all_colors":
        return {"vert", "jaune", "rouge", "bleu"}
    return {card["color"]}

def _hand_sizes(players, teams, n):
    """Taille de main cible par joueur selon regles.md §MISE EN PLACE :
       4 j. → 5 / 5 j. → 5 pour l'équipe de 3, 4 pour l'équipe de 2 / 6 j. → 4."""
    if n == 4:
        return {p: 5 for p in players}
    if n == 6:
        return {p: 4 for p in players}
    # 5 joueurs : la règle dépend de la taille de l'équipe
    sizes = {}
    for t in teams:
        s = 5 if len(t) == 3 else 4
        for p in t:
            sizes[p] = s
    return sizes

def deal_cards(deck, players, n, existing_teams=None, active_absolu_ids=None):
    """Distribue une main conformément à regles.md.

    - Manche 1 (existing_teams=None) : n Absolus sont tirés au sort et distribués
      face visible (un par joueur). Les 6-n Absolus restants sont écartés
      pour toute la partie. Les équipes sont formées à partir des Absolus tirés.
    - Manche 2+ (existing_teams fournies) : les n Absolus « actifs » (active_absolu_ids)
      sont remélangés avec les regulars ; les équipes restent identiques.
      Les joueurs peuvent recevoir 0 ou plusieurs Absolus en main (face cachée).

    Retourne (hands, absolu_dealt, teams, active_absolu_ids).
    `absolu_dealt` est vide en manche 2+ (les Absolus ne sont plus face visible)."""
    if n not in (4, 5, 6):
        raise ValueError(f"Nombre de joueurs invalide : {n}")
    all_absolus = [c for c in deck if c["is_absolu"]]
    regulars    = [c for c in deck if not c["is_absolu"]]
    hands = {p: [] for p in players}
    absolu_dealt = {}

    if existing_teams is None:
        # Manche 1 : piocher n Absolus, en donner un à chacun, former les équipes.
        random.shuffle(all_absolus)
        used_absolus = all_absolus[:n]
        for i, pid in enumerate(players):
            hands[pid].append(used_absolus[i])
            absolu_dealt[pid] = used_absolus[i]
        teams = form_teams(players, [absolu_dealt[p] for p in players])
        pool = regulars[:]
    else:
        # Manche 2+ : tous les Absolus actifs + regulars remélangés ensemble.
        active_ids = set(active_absolu_ids or [])
        used_absolus = [c for c in all_absolus if c["id"] in active_ids]
        teams = existing_teams
        pool = used_absolus + regulars

    random.shuffle(pool)
    target = _hand_sizes(players, teams, n)
    idx = 0
    for pid in players:
        while len(hands[pid]) < target[pid] and idx < len(pool):
            hands[pid].append(pool[idx])
            idx += 1
    return hands, absolu_dealt, teams, [a["id"] for a in used_absolus]

def form_teams(players, absolu_cards):
    n = len(players)
    sorted_p = sorted(zip(players, absolu_cards), key=lambda x: x[1]["value"])
    order = [p for p, _ in sorted_p]
    if n == 4:
        return [[order[0], order[3]], [order[1], order[2]]]
    elif n == 5:
        return [[order[0], order[4]], [order[1], order[2], order[3]]]
    elif n == 6:
        return [[order[0], order[5]], [order[1], order[4]], [order[2], order[3]]]
    return [players]

def resolve_trick(played: dict, hands: dict, orgueil_pid_override=None) -> dict:
    cards = list(played.values())
    msgs  = []
    all_colors_in_play = set()
    for c in cards:
        all_colors_in_play |= effective_colors(c)
    ignore_highest = any(c["effect_type"] == "ignore_highest" for c in cards)
    lowest_wins    = any(c["effect_type"] == "lowest_wins" for c in cards)
    # Le Miroir annule l'effet de La Tristesse (regles.md §Miroir)
    if lowest_wins and ignore_highest:
        ignore_highest = False
        msgs.append("🪞 Le Miroir annule l'effet de La Tristesse.")
    if ignore_highest:
        msgs.append("🌧️ La Tristesse : la carte de plus forte valeur est ignorée.")
    if lowest_wins:
        msgs.append("🪞 Le Miroir : la carte de plus FAIBLE valeur remporte le tour !")

    def eff_val(card):
        v = card["value"]
        if ignore_highest:
            max_v = max(c["value"] for c in cards)
            if v == max_v:
                return -1
        return v

    if lowest_wins:
        winner_pid = min(played.items(), key=lambda x: eff_val(x[1]))[0]
    else:
        winner_pid = max(played.items(), key=lambda x: eff_val(x[1]))[0]

    winner_card = played[winner_pid]
    to_discard = {winner_card["id"]}

    for pid, card in played.items():
        cid = card["id"]
        eff = card["effect_type"]
        if cid in to_discard:
            continue
        if eff == "unbreakable":
            pass
        elif eff in ("highest_own", "lowest_own"):
            col = card["color"]
            same = [(p2, c2) for p2, c2 in played.items() if col in effective_colors(c2)]
            if same:
                target = (max if eff == "highest_own" else min)(same, key=lambda x: x[1]["value"])
                to_discard.add(target[1]["id"])
                label = "forte" if eff == "highest_own" else "faible"
                msgs.append(f"→ {card['name']} défausse {target[1]['name']} (plus {label} {col}).")
        elif eff == "if_other_same":
            col = card["color"]
            others = [c2 for p2, c2 in played.items()
                      if col in effective_colors(c2) and c2["id"] != cid]
            if others:
                to_discard.add(cid)
        elif eff == "if_color":
            if card["effect_param"] in all_colors_in_play:
                to_discard.add(cid)
        elif eff == "if_lowest":
            if card["value"] == min(c2["value"] for c2 in cards):
                to_discard.add(cid)
        elif eff == "if_lone_color":
            col = card["color"]
            if sum(1 for c2 in cards if col in effective_colors(c2)) == 1:
                to_discard.add(cid)
        elif eff == "if_absolu":
            if any(c2["is_absolu"] for c2 in cards):
                to_discard.add(cid)
        elif eff == "lowest_all":
            bot = min(played.items(), key=lambda x: x[1]["value"])
            to_discard.add(bot[1]["id"])
            msgs.append(f"→ L'Harmonie défausse {bot[1]['name']} (plus faible en jeu).")
        elif eff == "all_jaune":
            jaunes = [c2 for c2 in cards if "jaune" in effective_colors(c2)]
            for jc in jaunes:
                to_discard.add(jc["id"])
            if jaunes:
                msgs.append(f"→ L'Hiver défausse {len(jaunes)} carte(s) jaune(s).")
        elif eff in ("all_colors", "orgueil", "loi", "reve", "jalousie", "secret",
                     "colere", "trahison", "absolu", "none"):
            pass

    chain_discards = {}
    for pid, card in played.items():
        if card["effect_type"] == "chain" and card["id"] in to_discard:
            # Si la carte a été déplacée par Le Rêve, le propriétaire diffère du slot
            owner = card.get("_owner", pid)
            # La Chance ne peut pas défausser La Peur (regles.md §La Chance)
            spare = [c for c in hands.get(owner, [])
                     if c["id"] != card["id"] and c["effect_type"] != "unbreakable"]
            if spare:
                extra = min(spare, key=lambda c: c["value"])
                chain_discards[owner] = extra
                msgs.append(f"⛓️ La Chance : défausse aussi {extra['name']}.")

    next_leader = winner_pid
    for pid, card in played.items():
        if card["effect_type"] == "orgueil":
            # « à votre gauche » = à gauche du joueur qui a POSÉ la carte d'Orgueil
            next_leader = orgueil_pid_override or winner_pid
            msgs.append("👑 L'Orgueil : le joueur à gauche commencera.")
            break

    returned  = {pid: card for pid, card in played.items() if card["id"] not in to_discard}
    discarded = [card for card in played.values() if card["id"] in to_discard]
    return {
        "winner": winner_pid, "discarded": discarded,
        "returned": returned, "chain_discards": chain_discards,
        "next_leader": next_leader, "messages": msgs,
    }

def check_win_condition(hands, teams):
    """Détermine si une équipe remporte la manche (regles.md §FIN DE LA MANCHE).
    Retourne (team_idx, winner_pid) ou None.
    Priorité : un joueur à 0 carte (grâce à La Chance) > 1 carte (+ plus forte valeur)."""
    zero = [pid for pid, h in hands.items() if len(h) == 0]
    one  = [(pid, h) for pid, h in hands.items() if len(h) == 1]
    if not zero and not one:
        return None

    def team_of(pid):
        return next((i for i, t in enumerate(teams) if pid in t), -1)

    # 0 carte (La Chance) bat toujours 1 carte
    if zero:
        # S'il y en a plusieurs, on prend arbitrairement le premier pour ouvrir le round
        winner_pid = zero[0]
        return (team_of(winner_pid), winner_pid)

    # Départage entre joueurs à 1 carte : plus forte valeur en main
    best_pid, _ = max(one, key=lambda x: x[1][0]["value"])
    return (team_of(best_pid), best_pid)

# ─────────────────────────────────────────────────────────────────
# GAME ROOM
# ─────────────────────────────────────────────────────────────────

class GameRoom:
    def __init__(self, room_id, host_id):
        self.room_id    = room_id
        self.host_id    = host_id
        self.players    = {}
        self.player_order = []
        self.state      = "lobby"
        self.hands      = {}
        self.teams      = []
        self.team_wins  = []
        self.current_trick = {}
        self.trick_leader  = ""
        self.trick_order   = []
        self.round_num  = 0
        self.game_id    = str(uuid.uuid4())
        self.started_at = int(time.time())
        self.absolu_dealt = {}
        self.dev_mode   = False
        self.pending_interaction = None
        self.loi_constraint      = None
        self.trick_review_result = None
        self._review_task        = None
        self.last_trick          = None
        self.discard_pile        = []
        self.active_absolu_ids   = []    # Absolus réellement utilisés dans la partie
        self.manche_winner_pid   = None  # joueur ouvrant la manche suivante
        self.turn_timer_seconds  = 10   # secondes par tour joueur humain
        self._turn_timer_task    = None  # asyncio Task de minuterie
        self.last_activity_at    = time.time()  # pour le monitor d'inactivité

    def add_player(self, pid, username):
        self.players[pid] = {"username": username, "ws": None}
        if pid not in self.player_order:
            self.player_order.append(pid)

    def _next_to_play(self):
        if self.state != "playing":
            return None
        for pid in self.trick_order:
            if pid not in self.current_trick:
                return pid
        return None

    def public_state(self, for_pid=None):
        team_info = [
            {"members": [{"id": p, "username": self.players[p]["username"]}
                          for p in t if p in self.players],
             "wins": self.team_wins[ti] if ti < len(self.team_wins) else 0}
            for ti, t in enumerate(self.teams)
        ]
        players_info = []
        for pid in self.player_order:
            if pid not in self.players:
                continue
            hand = self.hands.get(pid, [])
            hand_data = hand if pid == for_pid else [{"id": c["id"], "back": True} for c in hand]
            players_info.append({
                "id": pid, "username": self.players[pid]["username"],
                "hand": hand_data, "hand_count": len(hand),
                "is_you": pid == for_pid,
                "absolu": self.absolu_dealt.get(pid),
                "is_bot": pid.startswith("bot_"),
            })
        return {
            "room_id": self.room_id, "state": self.state, "round_num": self.round_num,
            "players": players_info, "teams": team_info,
            "current_trick": self.current_trick,
            "trick_leader": self.trick_leader, "trick_order": self.trick_order,
            "next_to_play": self._next_to_play(),
            "host_id": self.host_id, "dev_mode": self.dev_mode,
            "pending_interaction": self.pending_interaction,
            "loi_constraint": self.loi_constraint,
            "trick_review": self.trick_review_result,
            "last_trick": self.last_trick,
            "discard_pile": self.discard_pile[-20:],
            "turn_timer_seconds": self.turn_timer_seconds,
        }

rooms: dict = {}
sessions: dict = {}
player_room: dict = {}
BOT_NAMES = ["Arcana", "Sibyl", "Morrigan"]

# ─────────────────────────────────────────────────────────────────
# WS HELPERS
# ─────────────────────────────────────────────────────────────────

async def broadcast(room, msg, exclude=None):
    for pid, info in room.players.items():
        if pid == exclude: continue
        ws = info.get("ws")
        if ws:
            try: await ws.send_json(msg)
            except: info["ws"] = None

async def send_state(room):
    for pid, info in room.players.items():
        ws = info.get("ws")
        if ws:
            try: await ws.send_json({"type": "state", "data": room.public_state(for_pid=pid)})
            except: info["ws"] = None

async def send_to(room, pid, msg):
    ws = room.players.get(pid, {}).get("ws")
    if ws:
        try: await ws.send_json(msg)
        except: pass

def save_history(room, wt_idx):
    db = get_db()
    pi  = json.dumps({p: room.players[p]["username"] for p in room.players})
    ti  = json.dumps([[p for p in t] for t in room.teams])
    dur = int(time.time()) - room.started_at
    for pid in room.players:
        if pid.startswith("bot_"): continue
        tidx = next((i for i, t in enumerate(room.teams) if pid in t), -1)
        res  = "victoire" if tidx == wt_idx else "défaite"
        db.execute(
            "INSERT INTO game_history (id,player_id,game_id,result,players,teams,duration,played_at) VALUES (?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), pid, room.game_id, res, pi, ti, dur, int(time.time()))
        )
    db.commit(); db.close()

def _rotate(order, start):
    if start not in order: return order
    i = order.index(start)
    return order[i:] + order[:i]

def _left_of(order, pid):
    if pid not in order: return order[0]
    return order[(order.index(pid) + 1) % len(order)]

# ─────────────────────────────────────────────────────────────────
# TURN TIMER
# ─────────────────────────────────────────────────────────────────

def _cancel_turn_timer(room: GameRoom):
    t = room._turn_timer_task
    if t and not t.done():
        t.cancel()
    room._turn_timer_task = None

async def _start_turn_timer(room: GameRoom):
    _cancel_turn_timer(room)
    if room.turn_timer_seconds <= 0 or room.state != "playing":
        return
    nxt = room._next_to_play()
    if not nxt or nxt.startswith("bot_"):
        return
    pid_for_timer = nxt

    async def _expire():
        try:
            await asyncio.sleep(room.turn_timer_seconds)
        except asyncio.CancelledError:
            return
        if room.state != "playing" or room._next_to_play() != pid_for_timer:
            return
        hand = room.hands.get(pid_for_timer, [])
        if not hand:
            return
        valid = hand[:]
        if room.loi_constraint:
            d = room.loi_constraint["direction"]
            filtered = [c for c in hand if (d == "lower" and c["value"] < 15)
                        or (d == "higher" and c["value"] > 15)]
            if filtered:
                valid = filtered
        card = random.choice(valid)
        uname = room.players[pid_for_timer]["username"]
        await broadcast(room, {"type": "chat",
            "msg": f"⏰ {uname} joue automatiquement {card['name']} (temps écoulé)."})
        await _play_card_logic(room, pid_for_timer, card)

    room._turn_timer_task = asyncio.create_task(_expire())
    await broadcast(room, {"type": "turn_timer", "pid": nxt, "seconds": room.turn_timer_seconds})

# ─────────────────────────────────────────────────────────────────
# INACTIVITY MONITOR
# ─────────────────────────────────────────────────────────────────

async def _inactivity_monitor():
    while True:
        await asyncio.sleep(10)
        now = time.time()
        to_close = [rid for rid, r in list(rooms.items())
                    if r.state != "lobby" and now - r.last_activity_at > 30]
        for rid in to_close:
            room = rooms.pop(rid, None)
            if room:
                _cancel_turn_timer(room)
                await broadcast(room, {"type": "error",
                    "msg": "⏳ Partie fermée pour inactivité (30 secondes sans action)."})

# ─────────────────────────────────────────────────────────────────
# TRICK RESOLUTION
# ─────────────────────────────────────────────────────────────────

async def _resolve_and_advance(room: GameRoom):
    _cancel_turn_timer(room)
    orgueil_override = None
    for pid, card in room.current_trick.items():
        if card["effect_type"] == "orgueil":
            owner = card.get("_owner", pid)
            orgueil_override = _left_of(room.player_order, owner)
            break

    result = resolve_trick(room.current_trick, room.hands, orgueil_override)
    winner_pid  = result["winner"]
    winner_name = room.players[winner_pid]["username"]

    discarded_ids = {c["id"] for c in result["discarded"]}
    for p in room.player_order:
        played_c = room.current_trick.get(p)
        if played_c and played_c["id"] in discarded_ids:
            # _owner ≠ slot pour Le Rêve : la carte retourne à la main de celui qui l'a jouée
            owner = played_c.get("_owner", p)
            room.hands[owner] = [c for c in room.hands[owner] if c["id"] != played_c["id"]]
    for p, extra in result["chain_discards"].items():
        room.hands[p] = [c for c in room.hands[p] if c["id"] != extra["id"]]

    # Accumuler la pile de défausse
    room.discard_pile.extend(result["discarded"])
    for extra in result["chain_discards"].values():
        if not any(c["id"] == extra["id"] for c in room.discard_pile):
            room.discard_pile.append(extra)

    # Sauvegarder le pli pour affichage ultérieur
    room.last_trick = {
        "winner_pid": winner_pid, "winner_name": winner_name,
        "played": {p: c for p, c in room.current_trick.items()},
        "discarded_ids": list(discarded_ids),
        "chain_discard_ids": [c["id"] for c in result["chain_discards"].values()],
        "messages": result["messages"],
    }

    full_msg = " ".join([f"✅ {winner_name} remporte le pli !"] + result["messages"])
    room.state = "trick_review"
    room.trick_review_result = {
        "winner_pid": winner_pid, "winner_name": winner_name,
        "discarded": result["discarded"], "chain_discards": result["chain_discards"],
        "messages": result["messages"], "next_leader": result["next_leader"], "msg": full_msg,
    }
    auto_ms = 0  # L'hôte clique toujours sur Continuer (même en mode dev)
    await broadcast(room, {
        "type": "trick_review", "winner_pid": winner_pid, "winner_name": winner_name,
        "discarded": result["discarded"],
        "chain_discards": {p: c for p, c in result["chain_discards"].items()},
        "messages": result["messages"], "msg": full_msg, "auto_continue_ms": auto_ms,
    })
    await send_state(room)
    await broadcast(room, {"type": "chat", "msg": full_msg})
    if auto_ms > 0:
        room._review_task = asyncio.create_task(_auto_continue_trick(room, auto_ms / 1000))

async def _auto_continue_trick(room: GameRoom, delay: float):
    await asyncio.sleep(delay)
    if room.state == "trick_review":
        await _finalize_trick(room)

async def _finalize_trick(room: GameRoom):
    if room.state != "trick_review": return
    t = getattr(room, "_review_task", None)
    if t and not t.done(): t.cancel()
    result = room.trick_review_result
    win = check_win_condition(room.hands, room.teams)
    if win is not None:
        wt, winner_pid = win
        room.team_wins[wt] += 1
        room.manche_winner_pid = winner_pid  # ouvrira la manche suivante
        members = [room.players[p]["username"] for p in room.teams[wt] if p in room.players]
        winner_name = room.players[winner_pid]["username"] if winner_pid in room.players else "?"
        await broadcast(room, {"type": "chat",
            "msg": f"🏆 L'équipe {', '.join(members)} remporte la manche grâce à {winner_name} ! ({room.team_wins[wt]}/2)"})
        if room.team_wins[wt] >= 2:
            room.state = "gameover"
            save_history(room, wt)
            await broadcast(room, {"type": "gameover", "winning_team": wt, "team_wins": room.team_wins})
            await broadcast(room, {"type": "chat",
                "msg": f"🎉 Victoire ! L'équipe {', '.join(members)} gagne !"})
        else:
            room.state = "roundend"
            await send_state(room)
        return
    room.trick_leader  = result["next_leader"]
    room.trick_order   = _rotate(room.player_order, result["next_leader"])
    room.current_trick = {}
    room.loi_constraint = None
    room.trick_review_result = None
    room.state = "playing"
    await send_state(room)
    await _start_turn_timer(room)
    if room.dev_mode:
        asyncio.create_task(run_bots(room))

# ─────────────────────────────────────────────────────────────────
# BOT AI
# ─────────────────────────────────────────────────────────────────

def bot_choose_card(hand, current_trick, loi_constraint=None):
    played = list(current_trick.values())
    colors_now = set()
    for c in played:
        colors_now |= effective_colors(c)
    valid = hand[:]
    if loi_constraint and played:
        d = loi_constraint["direction"]
        filtered = [c for c in hand if (d == "lower" and c["value"] < 15)
                    or (d == "higher" and c["value"] > 15)]
        if filtered: valid = filtered

    def score(card):
        s = card["value"]
        eff = card["effect_type"]
        if eff == "if_color" and card.get("effect_param") in colors_now:
            s += 20
        elif eff == "if_lone_color":
            if sum(1 for c in played if card["color"] in effective_colors(c)) == 0:
                s += 15
        elif eff == "unbreakable":
            s -= 30
        elif eff in INTERACTIVE_EFFECTS:
            s -= 10
        return s

    return max(valid, key=score)

async def run_bots(room: GameRoom):
    while room.state == "playing":
        nxt = room._next_to_play()
        if not nxt or not nxt.startswith("bot_"): break
        await asyncio.sleep(0.85)
        hand = room.hands.get(nxt, [])
        if not hand: break
        card = bot_choose_card(hand, room.current_trick, room.loi_constraint)
        await _play_card_logic(room, nxt, card)
        if room.state != "playing": break

async def _play_card_logic(room: GameRoom, pid: str, card: dict):
    card["_owner"] = pid  # utilisé par Le Rêve pour retrouver la main d'origine
    room.current_trick[pid] = card
    uname = room.players[pid]["username"]
    await broadcast(room, {"type": "chat", "msg": f"🃏 {uname} joue {card['name']}."})
    eff    = card["effect_type"]
    is_bot = pid.startswith("bot_")

    if eff in INTERACTIVE_EFFECTS and not is_bot:
        room.state = "interactive"
        room.pending_interaction = {"type": eff, "actor_pid": pid, "card_id": card["id"]}
        await send_state(room)
        prompts = {
            "loi":      "La Loi : choisissez la contrainte (< ou > 15) pour les joueurs suivants.",
            "reve":     "Le Rêve : choisissez un joueur devant qui poser votre carte.",
            "jalousie": "La Jalousie : choisissez une carte en jeu à échanger avec la vôtre.",
            "secret":   "Le Secret : montrer votre main OU voir celle d'un autre ?",
            "colere":   "La Colère : choisissez une carte déjà en jeu à renvoyer en main.",
            "trahison": "La Trahison : échangez une carte de votre main avec une carte en jeu.",
            "absolu":   "L'Absolu : échangez une carte de votre main avec celle d'un joueur.",
        }
        await send_to(room, pid, {
            "type": "interaction_required", "interaction": eff,
            "message": prompts.get(eff, "Choisissez une action."),
            "played_cards": {p: c for p, c in room.current_trick.items()},
            "players": [{"id": p, "username": room.players[p]["username"]}
                        for p in room.player_order if p != pid and p in room.players],
        })
        return

    if eff == "loi":
        room.loi_constraint = {"direction": "lower", "threshold": 15}
        await broadcast(room, {"type": "chat",
            "msg": "⚖️ La Loi : les joueurs suivants doivent jouer une carte < 15 (si possible)."})
    elif eff in INTERACTIVE_EFFECTS and (is_bot or room.dev_mode):
        await broadcast(room, {"type": "chat",
            "msg": f"🤖 {uname} ignore l'effet interactif de {card['name']} (auto)."})

    if len(room.current_trick) == len(room.players):
        await _resolve_and_advance(room)
        if room.state == "playing" and room.dev_mode:
            asyncio.create_task(run_bots(room))
    else:
        await send_state(room)
        if room.dev_mode:
            asyncio.create_task(run_bots(room))

# ─────────────────────────────────────────────────────────────────
# FASTAPI
# ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    asyncio.create_task(_inactivity_monitor())
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

def get_current_user(session: str = Cookie(default=None)):
    if not session or session not in sessions:
        raise HTTPException(401, "Non authentifié")
    return sessions[session]

def require_admin(pid: str = Depends(get_current_user)):
    db = get_db()
    row = db.execute("SELECT is_admin, is_banned FROM users WHERE id=?", (pid,)).fetchone()
    db.close()
    if not row or not row["is_admin"] or row["is_banned"]:
        raise HTTPException(403, "Accès réservé aux administrateurs")
    return pid

class AuthBody(BaseModel):
    username: str
    password: str

class CreateRoomBody(BaseModel):
    timer_seconds: int = 10

class AdminResetPwBody(BaseModel):
    new_password: str

class AdminCreateUserBody(BaseModel):
    username: str
    password: str
    is_admin: bool = False

class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str

# ── Auth ──────────────────────────────────────────────────────────

@app.post("/api/register")
def register(body: AuthBody):
    raise HTTPException(403, "L'inscription publique est désactivée. Contactez l'administrateur.")

@app.post("/api/login")
def login(body: AuthBody):
    db = get_db()
    row = db.execute(
        "SELECT * FROM users WHERE username=? AND password_hash=?",
        (body.username.strip(), hash_pw(body.password))
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(401, "Identifiants incorrects")
    if row["is_banned"]:
        raise HTTPException(403, "Compte banni")
    token = str(uuid.uuid4()); sessions[token] = row["id"]
    resp = JSONResponse({"ok": True, "username": row["username"], "id": row["id"],
                         "is_admin": bool(row["is_admin"])})
    resp.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400*30)
    return resp

@app.post("/api/logout")
def logout(session: str = Cookie(default=None)):
    if session in sessions: del sessions[session]
    resp = JSONResponse({"ok": True}); resp.delete_cookie("session"); return resp

@app.get("/api/me")
def me(pid: str = Depends(get_current_user)):
    db = get_db()
    row = db.execute("SELECT id,username,is_admin FROM users WHERE id=?", (pid,)).fetchone()
    db.close()
    if not row: raise HTTPException(404)
    return {"id": row["id"], "username": row["username"], "is_admin": bool(row["is_admin"])}

@app.get("/api/history")
def history(pid: str = Depends(get_current_user)):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM game_history WHERE player_id=? ORDER BY played_at DESC LIMIT 50", (pid,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

# ── Rooms ─────────────────────────────────────────────────────────

@app.post("/api/rooms")
def create_room(body: CreateRoomBody, pid: str = Depends(get_current_user)):
    rid = str(uuid.uuid4())[:6].upper()
    room = GameRoom(rid, pid)
    room.turn_timer_seconds = body.timer_seconds if body.timer_seconds in (10, 15, 20) else 10
    rooms[rid] = room
    return {"room_id": rid}

@app.post("/api/rooms/dev")
def create_dev_room(pid: str = Depends(get_current_user)):
    rid = "DEV" + str(uuid.uuid4())[:3].upper()
    room = GameRoom(rid, pid); room.dev_mode = True; rooms[rid] = room
    for i, bn in enumerate(BOT_NAMES):
        bid = f"bot_{i}_{rid}"
        room.players[bid] = {"username": bn, "ws": None}
        room.player_order.append(bid)
    return {"room_id": rid}

@app.get("/api/rooms/{room_id}")
def get_room(room_id: str, pid: str = Depends(get_current_user)):
    room = rooms.get(room_id.upper())
    if not room: raise HTTPException(404, "Salon introuvable")
    return room.public_state(for_pid=pid)

# ── Classement ────────────────────────────────────────────────────

@app.get("/api/leaderboard")
def leaderboard(_pid: str = Depends(get_current_user)):
    db = get_db()
    rows = db.execute("""
        SELECT u.id, u.username,
               COUNT(CASE WHEN gh.result='victoire' THEN 1 END) AS wins,
               COUNT(CASE WHEN gh.result='défaite'  THEN 1 END) AS losses,
               COUNT(*) AS total
        FROM users u
        LEFT JOIN game_history gh ON gh.player_id = u.id
        WHERE u.is_banned = 0
        GROUP BY u.id
        ORDER BY wins DESC, total DESC
        LIMIT 50
    """).fetchall()
    db.close()
    result = []
    for r in rows:
        total = r["total"]
        ratio = round(r["wins"] / total * 100, 1) if total > 0 else 0
        result.append({
            "id": r["id"], "username": r["username"],
            "wins": r["wins"], "losses": r["losses"],
            "total": total, "ratio": ratio
        })
    return result

# ── Admin ─────────────────────────────────────────────────────────

@app.get("/api/admin/users")
def admin_list_users(_admin: str = Depends(require_admin)):
    db = get_db()
    rows = db.execute("""
        SELECT u.id, u.username, u.is_admin, u.is_banned, u.created_at,
               COUNT(CASE WHEN gh.result='victoire' THEN 1 END) AS wins,
               COUNT(CASE WHEN gh.result='défaite'  THEN 1 END) AS losses,
               COUNT(*) AS total_games
        FROM users u
        LEFT JOIN game_history gh ON gh.player_id = u.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
    """).fetchall()
    db.close()
    return [dict(r) for r in rows]

@app.post("/api/admin/users/{uid}/ban")
def admin_ban(uid: str, admin_pid: str = Depends(require_admin)):
    db = get_db()
    row = db.execute("SELECT username, is_admin FROM users WHERE id=?", (uid,)).fetchone()
    if not row: raise HTTPException(404)
    if row["is_admin"]: raise HTTPException(400, "Impossible de bannir un administrateur")
    db.execute("UPDATE users SET is_banned=1 WHERE id=?", (uid,))
    db.commit(); db.close()
    # Expulser les sessions actives du joueur banni
    to_del = [t for t, p in sessions.items() if p == uid]
    for t in to_del: del sessions[t]
    return {"ok": True}

@app.post("/api/admin/users/{uid}/unban")
def admin_unban(uid: str, _admin: str = Depends(require_admin)):
    db = get_db()
    db.execute("UPDATE users SET is_banned=0 WHERE id=?", (uid,))
    db.commit(); db.close()
    return {"ok": True}

@app.post("/api/admin/users/{uid}/reset-password")
def admin_reset_pw(uid: str, body: AdminResetPwBody, _admin: str = Depends(require_admin)):
    if len(body.new_password) < 4:
        raise HTTPException(400, "Mot de passe trop court")
    db = get_db()
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(body.new_password), uid))
    db.commit(); db.close()
    return {"ok": True}

@app.delete("/api/admin/users/{uid}")
def admin_delete_user(uid: str, admin_pid: str = Depends(require_admin)):
    db = get_db()
    row = db.execute("SELECT username, is_admin FROM users WHERE id=?", (uid,)).fetchone()
    if not row: raise HTTPException(404)
    if row["is_admin"]: raise HTTPException(400, "Impossible de supprimer un administrateur")
    db.execute("DELETE FROM game_history WHERE player_id=?", (uid,))
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit(); db.close()
    to_del = [t for t, p in sessions.items() if p == uid]
    for t in to_del: del sessions[t]
    return {"ok": True}

@app.get("/api/admin/rooms")
def admin_list_rooms(_admin: str = Depends(require_admin)):
    result = []
    for rid, room in rooms.items():
        result.append({
            "room_id": rid, "state": room.state,
            "player_count": len(room.players),
            "players": [room.players[p]["username"] for p in room.player_order],
            "round_num": room.round_num,
            "dev_mode": room.dev_mode,
            "started_at": room.started_at,
        })
    return result

@app.post("/api/admin/rooms/{rid}/close")
def admin_close_room(rid: str, _admin: str = Depends(require_admin)):
    room = rooms.get(rid.upper())
    if not room: raise HTTPException(404)
    rooms.pop(rid.upper(), None)
    return {"ok": True}

@app.post("/api/admin/rooms/close-all")
def admin_close_all_rooms(_admin: str = Depends(require_admin)):
    count = len(rooms)
    rooms.clear()
    return {"ok": True, "closed": count}

@app.post("/api/admin/create-user")
def admin_create_user(body: AdminCreateUserBody, _admin: str = Depends(require_admin)):
    if len(body.username) < 2 or len(body.password) < 4:
        raise HTTPException(400, "Nom ou mot de passe trop court (min 4 car.)")
    db = get_db(); uid = str(uuid.uuid4())
    try:
        db.execute(
            "INSERT INTO users (id,username,password_hash,is_admin,is_banned,created_at) VALUES (?,?,?,?,0,?)",
            (uid, body.username.strip(), hash_pw(body.password), 1 if body.is_admin else 0, int(time.time()))
        )
        db.commit()
    except Exception:
        raise HTTPException(400, "Nom d'utilisateur déjà pris")
    finally:
        db.close()
    return {"ok": True, "id": uid}

@app.get("/api/admin/export")
def admin_export(_admin: str = Depends(require_admin)):
    db = get_db()
    users   = [dict(r) for r in db.execute("SELECT * FROM users").fetchall()]
    history = [dict(r) for r in db.execute("SELECT * FROM game_history").fetchall()]
    db.close()
    return {"users": users, "game_history": history, "exported_at": int(time.time())}

class ImportBody(BaseModel):
    users: list
    game_history: list

@app.post("/api/admin/import")
def admin_import(body: ImportBody, _admin: str = Depends(require_admin)):
    db = get_db()
    for u in body.users:
        db.execute(
            "INSERT OR REPLACE INTO users (id,username,password_hash,is_admin,is_banned,created_at) VALUES (?,?,?,?,?,?)",
            (u["id"], u["username"], u["password_hash"], u.get("is_admin",0), u.get("is_banned",0), u.get("created_at",0))
        )
    for h in body.game_history:
        db.execute(
            "INSERT OR REPLACE INTO game_history (id,player_id,game_id,result,players,teams,duration,played_at) VALUES (?,?,?,?,?,?,?,?)",
            (h["id"], h["player_id"], h["game_id"], h["result"], h["players"], h["teams"], h.get("duration",0), h.get("played_at",0))
        )
    db.commit(); db.close()
    return {"ok": True}

@app.post("/api/admin/reset-stats")
def admin_reset_stats(_admin: str = Depends(require_admin)):
    db = get_db()
    db.execute("DELETE FROM game_history")
    db.commit(); db.close()
    return {"ok": True}

@app.post("/api/admin/users/{uid}/reset-stats")
def admin_reset_user_stats(uid: str, _admin: str = Depends(require_admin)):
    db = get_db()
    db.execute("DELETE FROM game_history WHERE player_id=?", (uid,))
    db.commit(); db.close()
    return {"ok": True}

@app.post("/api/change-password")
def change_password(body: ChangePasswordBody, pid: str = Depends(get_current_user)):
    if len(body.new_password) < 4:
        raise HTTPException(400, "Nouveau mot de passe trop court (min 4 car.)")
    db = get_db()
    row = db.execute("SELECT password_hash FROM users WHERE id=?", (pid,)).fetchone()
    if not row or row["password_hash"] != hash_pw(body.old_password):
        db.close()
        raise HTTPException(401, "Ancien mot de passe incorrect")
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(body.new_password), pid))
    db.commit(); db.close()
    return {"ok": True}

# ─────────────────────────────────────────────────────────────────
# WEBSOCKET
# ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/{room_id}")
async def ws_endpoint(websocket: WebSocket, room_id: str,
                      session: str = Cookie(default=None)):
    room_id = room_id.upper()
    if not session or session not in sessions:
        await websocket.close(code=4001); return
    pid = sessions[session]
    db = get_db()
    row = db.execute("SELECT username, is_banned FROM users WHERE id=?", (pid,)).fetchone()
    db.close()
    if not row or row["is_banned"]:
        await websocket.close(code=4002); return
    username = row["username"]
    if room_id not in rooms: await websocket.close(code=4004); return
    room = rooms[room_id]
    if room.state != "lobby" and pid not in room.players:
        await websocket.close(code=4003); return

    await websocket.accept()
    room.add_player(pid, username)
    room.players[pid]["ws"] = websocket
    player_room[pid] = room_id
    await send_state(room)
    await broadcast(room, {"type": "chat", "msg": f"✨ {username} a rejoint."}, exclude=pid)

    try:
        while True:
            raw = await websocket.receive_json()
            room.last_activity_at = time.time()
            act = raw.get("action")

            if act == "start" and pid == room.host_id:
                n = len(room.players)
                if n < 4 or n > 6:
                    await websocket.send_json({"type":"error","msg":f"Il faut 4–6 joueurs ({n} actuellement)"}); continue
                deck = build_deck()
                hands, absolu_dealt, teams, active_ids = deal_cards(deck, room.player_order, n)
                room.hands = hands; room.absolu_dealt = absolu_dealt; room.round_num = 1
                room.teams     = teams
                room.team_wins = [0] * len(room.teams)
                room.active_absolu_ids = active_ids
                room.manche_winner_pid = None
                # Manche 1 : plus fort Absolu ouvre (regles.md §DÉROULEMENT)
                leader = max(absolu_dealt.items(), key=lambda x: x[1]["value"])[0]
                room.trick_leader = leader
                room.trick_order  = _rotate(room.player_order, leader)
                room.current_trick = {}; room.loi_constraint = None; room.state = "playing"
                room.discard_pile = []; room.last_trick = None
                tag = " 🤖 [Mode Dev]" if room.dev_mode else ""
                await send_state(room)
                await broadcast(room, {"type":"chat",
                    "msg": f"🔮 La partie commence{tag} ! {room.players[leader]['username']} ouvre."})
                if room.dev_mode: asyncio.create_task(run_bots(room))
                await _start_turn_timer(room)

            elif act == "play_card":
                if room.state != "playing":
                    await websocket.send_json({"type":"error","msg":"Ce n'est pas le moment de jouer."}); continue
                if room._next_to_play() != pid:
                    await websocket.send_json({"type":"error","msg":"Ce n'est pas votre tour."}); continue
                cid  = raw.get("card_id")
                hand = room.hands.get(pid, [])
                card = next((c for c in hand if c["id"] == cid), None)
                if not card:
                    await websocket.send_json({"type":"error","msg":"Carte introuvable."}); continue
                if room.loi_constraint:
                    d   = room.loi_constraint["direction"]
                    can = any((d=="lower" and c["value"]<15) or (d=="higher" and c["value"]>15) for c in hand)
                    ok  = (d=="lower" and card["value"]<15) or (d=="higher" and card["value"]>15)
                    if can and not ok:
                        suf = "< 15" if d=="lower" else "> 15"
                        await websocket.send_json({"type":"error","msg":f"La Loi : jouez une carte {suf}."}); continue
                _cancel_turn_timer(room)
                await _play_card_logic(room, pid, card)

            elif act == "interaction_response":
                if room.state != "interactive": continue
                pi = room.pending_interaction
                if not pi or pi["actor_pid"] != pid: continue
                itype = pi["type"]

                if itype == "loi":
                    direction = raw.get("direction", "lower")
                    room.loi_constraint = {"direction": direction, "threshold": 15}
                    room.pending_interaction = None; room.state = "playing"
                    suf = "< 15" if direction == "lower" else "> 15"
                    await broadcast(room, {"type":"chat","msg": f"⚖️ La Loi : les joueurs suivants jouent {suf} si possible."})
                    await send_state(room)
                    if room.dev_mode: asyncio.create_task(run_bots(room))
                    await _start_turn_timer(room)

                elif itype == "jalousie":
                    tcard_id = raw.get("target_card_id")
                    tpid = next((p for p, c in room.current_trick.items() if c["id"] == tcard_id and p != pid), None)
                    my_card = room.current_trick.get(pid)
                    if tpid and my_card:
                        tc = room.current_trick[tpid]
                        room.current_trick[pid]  = tc
                        room.current_trick[tpid] = my_card
                        room.hands[pid]  = [tc  if c["id"] == my_card["id"] else c for c in room.hands[pid]]
                        room.hands[tpid] = [my_card if c["id"] == tc["id"] else c for c in room.hands[tpid]]
                        await broadcast(room, {"type":"chat","msg":f"🔀 La Jalousie : {username} échange avec {room.players[tpid]['username']}."})
                    room.pending_interaction = None; room.state = "playing"
                    if len(room.current_trick) == len(room.players):
                        await _resolve_and_advance(room)
                        if room.state=="playing" and room.dev_mode: asyncio.create_task(run_bots(room))
                    else:
                        await send_state(room)
                        if room.dev_mode: asyncio.create_task(run_bots(room))
                        await _start_turn_timer(room)

                elif itype == "secret":
                    choice = raw.get("choice", "show_to"); tpid = raw.get("target_pid")
                    if tpid and tpid in room.players:
                        if choice == "show_to":
                            await send_to(room, tpid, {"type":"secret_reveal","from":username,
                                "cards": room.hands.get(pid,[]), "msg":f"🔍 {username} vous montre sa main."})
                            await broadcast(room,{"type":"chat","msg":f"🤫 {username} montre sa main à {room.players[tpid]['username']}."})
                        else:
                            await send_to(room, pid, {"type":"secret_reveal",
                                "from":room.players[tpid]["username"],
                                "cards": room.hands.get(tpid,[]),
                                "msg":f"🔍 Vous voyez la main de {room.players[tpid]['username']}."})
                            await broadcast(room,{"type":"chat","msg":f"🤫 {username} regarde la main de {room.players[tpid]['username']}."})
                    room.pending_interaction = None; room.state = "playing"
                    if len(room.current_trick) == len(room.players):
                        await _resolve_and_advance(room)
                        if room.state=="playing" and room.dev_mode: asyncio.create_task(run_bots(room))
                    else:
                        await send_state(room)
                        if room.dev_mode: asyncio.create_task(run_bots(room))
                        await _start_turn_timer(room)

                elif itype == "colere":
                    tcard_id = raw.get("target_card_id")
                    tpid = next((p for p, c in room.current_trick.items() if c["id"] == tcard_id and p != pid), None)
                    if tpid:
                        returned = room.current_trick.pop(tpid, None)
                        # Si La Loi est renvoyée en main, sa contrainte tombe (regles.md §La Colère)
                        if returned and returned["effect_type"] == "loi" and room.loi_constraint:
                            room.loi_constraint = None
                            await broadcast(room,{"type":"chat","msg":"⚖️ La Loi est renvoyée en main : la contrainte est levée."})
                        await broadcast(room,{"type":"chat","msg":f"😡 La Colère : {room.players[tpid]['username']} doit rejouer !"})
                    room.pending_interaction = None; room.state = "playing"
                    await send_state(room)
                    if room.dev_mode: asyncio.create_task(run_bots(room))
                    await _start_turn_timer(room)

                elif itype == "trahison":
                    my_cid  = raw.get("hand_card_id"); tcard_id = raw.get("target_card_id")
                    tpid = next((p for p, c in room.current_trick.items() if c["id"] == tcard_id and p != pid), None)
                    my_card = next((c for c in room.hands.get(pid,[]) if c["id"] == my_cid), None)
                    if tpid and my_card:
                        tc = room.current_trick[tpid]
                        room.current_trick[tpid] = my_card
                        room.hands[pid]  = [tc if c["id"] == my_cid else c for c in room.hands[pid]]
                        room.hands[tpid] = [my_card if c["id"] == tc["id"] else c for c in room.hands[tpid]]
                        await broadcast(room,{"type":"chat","msg":f"🗡️ La Trahison : {username} substitue une carte à {room.players[tpid]['username']}."})
                        # Si La Loi revient en main, sa contrainte tombe (regles.md §La Trahison)
                        if tc["effect_type"] == "loi" and room.loi_constraint:
                            room.loi_constraint = None
                            await broadcast(room,{"type":"chat","msg":"⚖️ La Loi est renvoyée en main : la contrainte est levée."})
                    room.pending_interaction = None; room.state = "playing"
                    if len(room.current_trick) == len(room.players):
                        await _resolve_and_advance(room)
                        if room.state=="playing" and room.dev_mode: asyncio.create_task(run_bots(room))
                    else:
                        await send_state(room)
                        if room.dev_mode: asyncio.create_task(run_bots(room))
                        await _start_turn_timer(room)

                elif itype == "reve":
                    tpid = raw.get("target_pid")
                    my_card = room.current_trick.get(pid)
                    if not my_card:
                        room.pending_interaction = None; room.state = "playing"
                        await send_state(room); continue

                    # Cible = soi-même, invalide ou déjà joué → sans effet (regles.md §Le Rêve)
                    if tpid == pid or tpid not in room.players or tpid in room.current_trick:
                        await broadcast(room,{"type":"chat","msg":f"💭 Le Rêve : joué sans cible valide, sans effet."})
                        room.pending_interaction = None; room.state = "playing"
                        if len(room.current_trick) == len(room.players):
                            await _resolve_and_advance(room)
                            if room.state=="playing" and room.dev_mode: asyncio.create_task(run_bots(room))
                        else:
                            await send_state(room)
                            if room.dev_mode: asyncio.create_task(run_bots(room))
                            await _start_turn_timer(room)
                        continue

                    # Déplacer Le Rêve : slot actif → slot cible (owner reste l'actif)
                    room.current_trick[tpid] = my_card
                    room.current_trick.pop(pid, None)
                    await broadcast(room,{"type":"chat",
                        "msg":f"💭 Le Rêve : {username} pose sa carte devant {room.players[tpid]['username']}, qui doit poser une carte."})

                    # Cible = bot : auto-play immédiat
                    if tpid.startswith("bot_"):
                        await asyncio.sleep(0.6)
                        bot_hand = room.hands.get(tpid, [])
                        if bot_hand:
                            bot_card = bot_choose_card(bot_hand, room.current_trick, room.loi_constraint)
                            bot_card["_owner"] = tpid
                            room.current_trick[pid] = bot_card
                            await broadcast(room,{"type":"chat",
                                "msg":f"🃏 {room.players[tpid]['username']} pose {bot_card['name']} devant {username}."})
                            # Effet immédiat de Loi : s'applique ; autres effets interactifs : ignorés par le bot
                            if bot_card["effect_type"] == "loi":
                                room.loi_constraint = {"direction": "lower", "threshold": 15}
                                await broadcast(room,{"type":"chat",
                                    "msg":"⚖️ La Loi : les joueurs suivants doivent jouer une carte < 15 (si possible)."})
                        room.pending_interaction = None; room.state = "playing"
                        if len(room.current_trick) == len(room.players):
                            await _resolve_and_advance(room)
                            if room.state=="playing" and room.dev_mode: asyncio.create_task(run_bots(room))
                        else:
                            await send_state(room)
                            if room.dev_mode: asyncio.create_task(run_bots(room))
                            await _start_turn_timer(room)
                        continue

                    # Cible humaine : demander une carte en réponse
                    room.pending_interaction = {
                        "type": "reve_response",
                        "responder_pid": tpid,
                        "back_to_pid":   pid,
                    }
                    room.state = "interactive"
                    await send_state(room)
                    await send_to(room, tpid, {
                        "type": "interaction_required", "interaction": "reve_response",
                        "message": f"Le Rêve : posez une carte de votre main devant {username}.",
                        "hand": room.hands.get(tpid, []),
                        "back_to_username": username,
                    })

                elif itype == "reve_response":
                    responder_pid = pi.get("responder_pid")
                    if pid != responder_pid: continue
                    back_to = pi["back_to_pid"]
                    cid = raw.get("card_id")
                    card = next((c for c in room.hands.get(pid, []) if c["id"] == cid), None)
                    if not card:
                        await websocket.send_json({"type":"error","msg":"Carte introuvable."}); continue

                    # Contrainte de La Loi s'applique aussi à la réponse (regles.md §La Loi)
                    if room.loi_constraint:
                        d   = room.loi_constraint["direction"]
                        can = any((d=="lower" and c["value"]<15) or (d=="higher" and c["value"]>15)
                                  for c in room.hands.get(pid, []))
                        ok  = (d=="lower" and card["value"]<15) or (d=="higher" and card["value"]>15)
                        if can and not ok:
                            suf = "< 15" if d=="lower" else "> 15"
                            await websocket.send_json({"type":"error","msg":f"La Loi : jouez une carte {suf}."}); continue

                    card["_owner"] = pid  # carte venue de la main du responder
                    room.current_trick[back_to] = card
                    await broadcast(room,{"type":"chat",
                        "msg":f"🃏 {username} pose {card['name']} devant {room.players[back_to]['username']}."})

                    eff = card["effect_type"]
                    # Effet interactif : c'est le responder qui pilote la suite
                    if eff in INTERACTIVE_EFFECTS:
                        room.pending_interaction = {"type": eff, "actor_pid": pid, "card_id": card["id"]}
                        room.state = "interactive"
                        await send_state(room)
                        prompts = {
                            "loi":      "La Loi : choisissez la contrainte (< ou > 15) pour les joueurs suivants.",
                            "reve":     "Le Rêve : choisissez un joueur devant qui poser votre carte.",
                            "jalousie": "La Jalousie : choisissez une carte en jeu à échanger avec la vôtre.",
                            "secret":   "Le Secret : montrer votre main OU voir celle d'un autre ?",
                            "colere":   "La Colère : choisissez une carte déjà en jeu à renvoyer en main.",
                            "trahison": "La Trahison : échangez une carte de votre main avec une carte en jeu.",
                            "absolu":   "L'Absolu : échangez une carte de votre main avec celle d'un joueur.",
                        }
                        await send_to(room, pid, {
                            "type": "interaction_required", "interaction": eff,
                            "message": prompts.get(eff, "Choisissez une action."),
                            "played_cards": {p: c for p, c in room.current_trick.items()},
                            "players": [{"id": p, "username": room.players[p]["username"]}
                                        for p in room.player_order if p != pid and p in room.players],
                        })
                        continue

                    room.pending_interaction = None; room.state = "playing"
                    if len(room.current_trick) == len(room.players):
                        await _resolve_and_advance(room)
                        if room.state=="playing" and room.dev_mode: asyncio.create_task(run_bots(room))
                    else:
                        await send_state(room)
                        if room.dev_mode: asyncio.create_task(run_bots(room))
                        await _start_turn_timer(room)

                elif itype == "absolu":
                    tpid = raw.get("target_pid"); my_cid = raw.get("my_card_id")
                    if tpid and my_cid and tpid in room.players:
                        mc = next((c for c in room.hands.get(pid, []) if c["id"] == my_cid), None)
                        their_hand = room.hands.get(tpid, [])
                        tc_card = random.choice(their_hand) if their_hand else None
                        if mc and tc_card:
                            room.hands[pid]  = [tc_card if c["id"] == my_cid else c for c in room.hands[pid]]
                            room.hands[tpid] = [mc if c["id"] == tc_card["id"] else c for c in room.hands[tpid]]
                            await broadcast(room, {"type": "chat",
                                "msg": f"✨ L'Absolu : {username} échange {mc['name']} avec une carte de {room.players[tpid]['username']}."})
                    room.pending_interaction = None; room.state = "playing"
                    await send_state(room)
                    if room.dev_mode: asyncio.create_task(run_bots(room))
                    await _start_turn_timer(room)

            elif act == "continue_trick" and pid == room.host_id:
                if room.state == "trick_review":
                    await _finalize_trick(room)

            elif act == "new_round" and pid == room.host_id:
                if room.state != "roundend": continue
                deck = build_deck()
                # Équipes figées, Absolus actifs idem (regles.md §FIN DE LA MANCHE)
                hands, _, _, _ = deal_cards(
                    deck, room.player_order, len(room.players),
                    existing_teams=room.teams,
                    active_absolu_ids=room.active_absolu_ids,
                )
                room.hands = hands; room.absolu_dealt = {}; room.round_num += 1
                # Manche 2+ : le gagnant de la manche précédente ouvre
                leader = room.manche_winner_pid or room.player_order[0]
                room.trick_leader = leader; room.trick_order = _rotate(room.player_order, leader)
                room.current_trick = {}; room.loi_constraint = None; room.state = "playing"
                room.discard_pile = []; room.last_trick = None
                await send_state(room)
                await broadcast(room,{"type":"chat","msg":f"🔮 Manche {room.round_num} ! {room.players[leader]['username']} ouvre."})
                if room.dev_mode: asyncio.create_task(run_bots(room))
                await _start_turn_timer(room)

            elif act == "restart" and pid == room.host_id:
                if room.state != "gameover": continue
                _cancel_turn_timer(room)
                dev = room.dev_mode
                room.players      = {k:v for k,v in room.players.items() if not k.startswith("bot_")}
                room.player_order = [p for p in room.player_order if not p.startswith("bot_")]
                if dev:
                    for i, bn in enumerate(BOT_NAMES):
                        bid = f"bot_{i}_{room.room_id}"
                        room.players[bid] = {"username": bn, "ws": None}
                        room.player_order.append(bid)
                room.state="lobby"; room.hands={}; room.teams=[]; room.team_wins=[]
                room.current_trick={}; room.trick_leader=""; room.trick_order=[]
                room.round_num=0; room.loi_constraint=None; room.pending_interaction=None
                room.game_id=str(uuid.uuid4()); room.started_at=int(time.time())
                room.active_absolu_ids=[]; room.manche_winner_pid=None
                room.absolu_dealt={}; room.discard_pile=[]; room.last_trick=None
                await send_state(room)
                await broadcast(room,{"type":"chat","msg":"🔄 Nouvelle partie !"})

            elif act == "chat":
                text = str(raw.get("text","")).strip()[:200]
                if text:
                    await broadcast(room,{"type":"chat","msg":f"💬 {username} : {text}"})

    except WebSocketDisconnect:
        pass
    finally:
        if pid in room.players: room.players[pid]["ws"] = None
        await broadcast(room,{"type":"chat","msg":f"👋 {username} a quitté."})
        if room.state == "lobby" and all(v.get("ws") is None for v in room.players.values()):
            rooms.pop(room_id, None)

@app.get("/")
def serve_index():
    return FileResponse("index.html")