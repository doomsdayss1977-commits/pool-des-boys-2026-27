"""Moteur du pool : règlements, participants, roue, ordre de sélection, repêchage serpentin."""
import random
import time
import uuid

STEPS = ["rules", "participants", "wheel", "teams", "order", "draft", "season"]

DEFAULT_RULES = {
    "roster": {"F": 6, "D": 4, "G": 1},
    "snake": True,
    "timerSec": 0,
    "maxReplacements": 2,       # remplacements (blessé/inactif) permis par participant et par saison
    "tradeDeadline": "",        # AAAA-MM-JJ ; vide = pas de limite
    "playoffs": True,           # classement séparé des séries (stats gameType 3)
    "points": {
        "goal": 1, "assist": 1, "teamWin": 2, "goalieWin": 2, "shutout": 3,
        # suggestions (à 0 par défaut, activables dans l'écran Règlements)
        "goalieOtl": 0, "ppGoal": 0, "shGoal": 0, "gwg": 0, "otGoal": 0,
        "plusMinus": 0, "goalieGoalAssist": 0, "teamOtl": 0,
    },
}

PALETTE = ["#E63946", "#2A9D8F", "#F4A261", "#457B9D", "#8338EC", "#FFBE0B",
           "#06D6A0", "#EF476F", "#118AB2", "#FB5607", "#3A86FF", "#80ED99"]


def new_pool(name, teams, prev_season, cur_season):
    return {
        "id": uuid.uuid4().hex[:10],
        "name": name or "Mon pool",
        "createdAt": time.strftime("%Y-%m-%d %H:%M"),
        "step": "rules",
        "rules": {"roster": dict(DEFAULT_RULES["roster"]), "snake": True, "timerSec": 0,
                  "maxReplacements": 2, "tradeDeadline": "", "playoffs": True,
                  "points": dict(DEFAULT_RULES["points"]),
                  "prevSeason": prev_season, "season": cur_season},
        "participants": [],
        "teams": teams,
        "spinOrder": [],
        "order": [],
        "picks": [],
        "moves": [],
        "stats": None,
    }


def roster_size(rules):
    return sum(rules["roster"].values())


def add_participant(pool, name):
    pid = uuid.uuid4().hex[:8]
    color = PALETTE[len(pool["participants"]) % len(PALETTE)]
    pool["participants"].append({"id": pid, "name": name.strip(), "color": color, "team": None, "wishlist": []})
    return pid


def remove_participant(pool, pid):
    pool["participants"] = [p for p in pool["participants"] if p["id"] != pid]


def available_teams(pool):
    taken = {p["team"] for p in pool["participants"] if p["team"]}
    return [t for t in pool["teams"] if t["abbr"] not in taken]


def participant(pool, pid):
    p = next((x for x in pool["participants"] if x["id"] == pid), None)
    if p is None:
        raise ValueError("Participant inconnu")
    return p


def assign_team(pool, pid, abbr):
    if abbr not in {t["abbr"] for t in available_teams(pool)}:
        raise ValueError("Équipe déjà attribuée")
    participant(pool, pid)["team"] = abbr


def remaining_spinners(pool):
    done = set(pool.get("spinOrder", []))
    return [p for p in pool["participants"] if p["id"] not in done]


def spin(pool, rng=random):
    """Tire au hasard le prochain participant : il choisira son équipe LNH à ce rang (l'UI anime la roue)."""
    avail = remaining_spinners(pool)
    if not avail:
        raise ValueError("Tous les participants sont déjà tirés")
    p = rng.choice(avail)
    pool.setdefault("spinOrder", []).append(p["id"])
    return p


def next_chooser(pool):
    """Participant dont c'est le tour de choisir son équipe, selon l'ordre tiré à la roue."""
    for pid in pool.get("spinOrder", []):
        p = participant(pool, pid)
        if p["team"] is None:
            return p
    return None


def choose_team(pool, pid, abbr):
    nxt = next_chooser(pool)
    if nxt is None or nxt["id"] != pid:
        raise ValueError("Ce n'est pas le tour de ce participant")
    assign_team(pool, pid, abbr)
    return next(t for t in pool["teams"] if t["abbr"] == abbr)


def compute_order(pool):
    """Le participant dont l'équipe a fini dernière repêche 1er, etc."""
    rank = {t["abbr"]: t["rank"] for t in pool["teams"]}
    parts = pool["participants"]
    if any(p["team"] is None for p in parts):
        raise ValueError("Tous les participants doivent avoir une équipe")
    ordered = sorted(parts, key=lambda p: -rank[p["team"]])
    pool["order"] = [p["id"] for p in ordered]
    return pool["order"]


def total_picks(pool):
    return len(pool["order"]) * roster_size(pool["rules"])


def pick_at(pool, i):
    """Sélection n° i (0-based) : ronde, rang dans la ronde et participant, en serpentin si activé."""
    n = len(pool["order"])
    r, slot = divmod(i, n)
    pid = pool["order"][n - 1 - slot if pool["rules"]["snake"] and r % 2 else slot]
    return {"overall": i + 1, "round": r + 1, "slot": slot + 1, "participantId": pid}


def pick_sequence(pool):
    return [pick_at(pool, i) for i in range(total_picks(pool))]


def current_pick(pool):
    i = len(pool["picks"])
    return pick_at(pool, i) if pool["order"] and i < total_picks(pool) else None


def all_needs(pool, players):
    """{participantId: {F, D, G} restant à combler} en une seule passe sur les sélections."""
    lim = pool["rules"]["roster"]
    out = {p["id"]: dict(lim) for p in pool["participants"]}
    for pk in pool["picks"]:
        out[pk["participantId"]][players[str(pk["playerId"])]["pos"]] -= 1
    return out


def needs(pool, pid, players):
    return all_needs(pool, players)[pid]


def make_pick(pool, player_id, players):
    cur = current_pick(pool)
    if cur is None:
        raise ValueError("Le repêchage est terminé")
    key = str(player_id)
    if key not in players:
        raise ValueError("Joueur inconnu")
    if any(str(pk["playerId"]) == key for pk in pool["picks"]):
        raise ValueError("Ce joueur est déjà sélectionné")
    pl = players[key]
    if needs(pool, cur["participantId"], players)[pl["pos"]] <= 0:
        raise ValueError({"F": "Attaquants complets", "D": "Défenseurs complets", "G": "Gardien déjà choisi"}[pl["pos"]])
    pick = dict(cur, playerId=int(player_id), at=time.strftime("%H:%M:%S"))
    pool["picks"].append(pick)
    if current_pick(pool) is None:
        pool["step"] = "season"
    return pick


def undo_pick(pool):
    if not pool["picks"]:
        raise ValueError("Aucune sélection à annuler")
    pool["step"] = "draft"
    return pool["picks"].pop()


def auto_pick(pool, players, rng=random):
    """Meilleur joueur disponible (points saison précédente) qui respecte les besoins du participant."""
    cur = current_pick(pool)
    if cur is None:
        return None
    nd = needs(pool, cur["participantId"], players)
    taken = {str(pk["playerId"]) for pk in pool["picks"]}

    pts = pool["rules"]["points"]

    def score(p):
        s = p.get("prev") or {}
        if p["pos"] == "G":
            return s.get("w", 0) * pts["goalieWin"] + s.get("so", 0) * pts["shutout"]
        return s.get("pts", 0) + rng.random() * 0.01

    # 1) liste de souhaits du participant, dans l'ordre ; 2) meilleur joueur disponible
    for wid in participant(pool, cur["participantId"]).get("wishlist", []):
        p = players.get(str(wid))
        if p and str(wid) not in taken and nd[p["pos"]] > 0:
            return make_pick(pool, wid, players)
    cands = [p for p in players.values() if str(p["id"]) not in taken and nd[p["pos"]] > 0]
    # Priorise les postes à remplir en proportion du manque restant
    remaining = sum(nd.values())
    best = max(cands, key=lambda p: score(p) * (1 + nd[p["pos"]] / remaining))
    return make_pick(pool, best["id"], players)




# ---------------- alignements en saison : remplacements et échanges ----------------

def rosters(pool):
    """{participantId: [ligne]} — ligne = {playerId, round, overall, baseline?, frozenFp?, since?}.
    Part des sélections du repêchage puis applique les transactions dans l'ordre."""
    out = {p["id"]: [] for p in pool["participants"]}
    for pk in pool["picks"]:
        out[pk["participantId"]].append({"playerId": pk["playerId"], "round": pk["round"], "overall": pk["overall"]})
    for mv in pool.get("moves", []):
        if mv["type"] == "replace":
            _swap(out[mv["participantId"]], mv["out"], mv["in"], mv)
        elif mv["type"] == "trade":
            for side, other in ((mv["a"], mv["b"]), (mv["b"], mv["a"])):
                for o, i in zip(side["gives"], other["gives"]):
                    _swap(out[side["participantId"]], o, i, mv)
    return out


def _swap(lines, out_pl, in_pl, mv):
    for l in lines:
        if l["playerId"] == out_pl["playerId"] and "gone" not in l:
            l["gone"] = mv["date"]
            l["frozenFp"] = out_pl.get("frozenFp", 0)
            break
    lines.append({"playerId": in_pl["playerId"], "round": None, "overall": None, "baseline": in_pl.get("baseline"),
                  "since": mv["date"], "via": mv["type"]})


def active_roster(pool, pid):
    return [l for l in rosters(pool)[pid] if "gone" not in l]


def owner_of(pool, player_id):
    for pid, lines in rosters(pool).items():
        if any(l["playerId"] == player_id and "gone" not in l for l in lines):
            return pid
    return None


def _check_deadline(pool, today):
    dl = pool["rules"].get("tradeDeadline")
    if dl and today > dl:
        raise ValueError(f"Date limite des transactions dépassée ({dl})")


def replace_player(pool, pid, out_id, in_id, players, stats, today):
    """Remplacement blessé/inactif : même position, joueur libre, quota maxReplacements."""
    _check_deadline(pool, today)
    used = sum(1 for m in pool.get("moves", []) if m["type"] == "replace" and m["participantId"] == pid)
    if used >= pool["rules"].get("maxReplacements", 2):
        raise ValueError("Quota de remplacements atteint")
    if owner_of(pool, out_id) != pid:
        raise ValueError("Ce joueur n'est pas dans cet alignement")
    if owner_of(pool, in_id) is not None:
        raise ValueError("Ce joueur appartient déjà à un participant")
    po, pi = players[str(out_id)], players[str(in_id)]
    if po["pos"] != pi["pos"]:
        raise ValueError("Le remplaçant doit jouer à la même position")
    mv = {"type": "replace", "date": today, "participantId": pid,
          "out": {"playerId": out_id, "frozenFp": stats.get("fp", {}).get(str(out_id), 0)},
          "in": {"playerId": in_id, "baseline": stats.get("lines", {}).get(str(in_id))}}
    pool.setdefault("moves", []).append(mv)
    return mv


def trade(pool, pid_a, gives_a, pid_b, gives_b, players, stats, today):
    """Échange 1-pour-1 ou N-pour-N, position par position (l'alignement 6/4/1 reste respecté)."""
    _check_deadline(pool, today)
    if pid_a == pid_b or not gives_a or len(gives_a) != len(gives_b):
        raise ValueError("Échange invalide : il faut le même nombre de joueurs de chaque côté")
    for pid, ids in ((pid_a, gives_a), (pid_b, gives_b)):
        for i in ids:
            if owner_of(pool, i) != pid:
                raise ValueError(f"{players[str(i)]['last']} n'appartient pas au bon participant")
    pos_a = sorted(players[str(i)]["pos"] for i in gives_a)
    pos_b = sorted(players[str(i)]["pos"] for i in gives_b)
    if pos_a != pos_b:
        raise ValueError("Les positions échangées doivent correspondre (ex. un défenseur contre un défenseur)")
    # apparie chaque joueur donné avec un joueur reçu de même position
    remaining = list(gives_b)
    paired_b = []
    for i in gives_a:
        j = next(x for x in remaining if players[str(x)]["pos"] == players[str(i)]["pos"])
        remaining.remove(j)
        paired_b.append(j)
    line = lambda i: {"playerId": i, "frozenFp": stats.get("fp", {}).get(str(i), 0), "baseline": stats.get("lines", {}).get(str(i))}
    mv = {"type": "trade", "date": today,
          "a": {"participantId": pid_a, "gives": [line(i) for i in gives_a]},
          "b": {"participantId": pid_b, "gives": [line(i) for i in paired_b]}}
    pool.setdefault("moves", []).append(mv)
    return mv


def undo_last_move(pool):
    if not pool.get("moves"):
        raise ValueError("Aucune transaction à annuler")
    return pool["moves"].pop()
