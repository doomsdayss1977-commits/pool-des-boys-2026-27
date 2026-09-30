"""Calcul quotidien complet du pool — partagé par l'app (main.py) et le robot GitHub (update_pool.py)."""
import datetime as dt

import draft
import scoring


def _totals(rows):
    return {r["participant"]["id"]: r["total"] for r in rows}


def flags(pool, players, stats, cur_teams):
    """Signaux par joueur : matchs manqués (matchs de l'équipe − matchs du joueur) et changement d'équipe."""
    team_gp = {t["abbr"]: t.get("gp", 0) for t in cur_teams or []}
    out = {}
    for pid, lines in draft.rosters(pool).items():
        for l in lines:
            if "gone" in l:
                continue
            pl = players[str(l["playerId"])]
            st = (stats or {}).get(str(pl["id"])) or {}
            cur_team = st.get("team") or pl["team"]
            missed = max(0, team_gp.get(cur_team, 0) - st.get("gp", 0)) if team_gp.get(cur_team) else 0
            f = {}
            if cur_team != pl["team"] or len(st.get("teams", [])) > 1:
                f["traded"] = cur_team
            if missed >= 3:
                f["missed"] = missed
            if f:
                out[str(pl["id"])] = f
    return out


GAMES = 82


def _extras(pool, players, stats, cur_teams, rows, phist, today, week_games):
    """Projection 82 matchs, forme sur 7 jours, répartition des points, matchs à venir.
    phist = {date: {playerId: [pts fantasy bruts, PJ]}} (joueurs des alignements, 15 jours)."""
    pts = pool["rules"]["points"]
    team_gp = {t["abbr"]: t.get("gp", 0) for t in cur_teams or []}
    stats = stats or {}
    snap = {}
    for r in rows:
        for l in r["lines"]:
            if not l["gone"]:
                st = l["stat"] or {}
                snap[str(l["player"]["id"])] = [scoring.player_points(l["player"], st, pts), st.get("gp", 0)]
    phist = {d: v for d, v in (phist or {}).items() if d < today}
    phist[today] = snap
    phist = {d: phist[d] for d in sorted(phist)[-15:]}
    week_ago = (dt.date.fromisoformat(today) - dt.timedelta(days=7)).isoformat()
    base = next((phist[d] for d in sorted(phist, reverse=True) if d <= week_ago), None)
    hot = []
    for r in rows:
        split = {"F": 0, "D": 0, "G": 0, "T": r["teamPts"]}
        proj, games = r["teamPts"], 0
        tgp = team_gp.get(r["participant"]["team"], 0)
        proj_ok = bool(tgp)
        if tgp:
            proj += r["teamPts"] / tgp * max(0, GAMES - tgp)
        for l in r["lines"]:
            pl = l["player"]
            split[pl["pos"]] += l["fp"]
            if l["gone"]:
                proj += l["fp"]
                continue
            st = l["stat"] or {}
            cur = st.get("team") or pl["team"]
            games += (week_games or {}).get(cur, 0)
            g = team_gp.get(cur, 0)
            raw, gp = snap[str(pl["id"])]
            l["proj"] = l["fp"] + (raw / g * max(0, GAMES - g) if g else 0)
            proj += l["proj"]
            if base is not None:
                b = base.get(str(pl["id"]))
                l["f7"], l["gp7"] = (raw - b[0], gp - b[1]) if b else (None, None)
                if l["f7"] is not None:
                    hot.append((r["participant"], l))
        r["split"] = split
        r["proj"] = round(proj, 1) if proj_ok else None
        r["weekGames"] = games if week_games else None
    card = lambda p, l: {"who": p["name"], "color": p["color"], "player": l["player"], "f7": l["f7"], "gp7": l["gp7"]}
    fire = [card(p, l) for p, l in sorted(hot, key=lambda x: -x[1]["f7"]) if l["f7"] > 0][:6]
    ice = [card(p, l) for p, l in sorted(hot, key=lambda x: -x[1]["gp7"]) if l["f7"] <= 0 and l["gp7"] >= 3 and l["player"]["pos"] != "G"][:6]
    return phist, fire, ice


def compute(pool, players, stats, cur_teams, playoff_stats, history, prev, today=None, phist=None, week_games=None):
    """Retourne tout ce que la page et l'app affichent.
    history = {date: {participantId: total}} (tendance) ; prev = {"date", "players"} = stats de la dernière passe (points d'hier)."""
    today = today or dt.date.today().isoformat()
    rows = scoring.standings(pool, players, stats, cur_teams)
    phist, fire, ice = _extras(pool, players, stats, cur_teams, rows, phist, today, week_games)
    history = dict(history or {})
    history[today] = _totals(rows)
    dates = sorted(history)
    # points d'hier / de la semaine par participant
    deltas = scoring.daily_deltas(prev.get("players") if prev and prev.get("date") != today else None, stats, pool, players) if prev else {}
    week_ago = (dt.date.fromisoformat(today) - dt.timedelta(days=7)).isoformat()
    base_week = next((history[d] for d in reversed(dates) if d <= week_ago), None)
    for r in rows:
        pid = r["participant"]["id"]
        lines = [(l, deltas[str(l["player"]["id"])]) for l in r["lines"] if not l["gone"] and str(l["player"]["id"]) in deltas]
        r["yesterday"] = {"fp": sum(d["fp"] for _, d in lines),
                          "lines": [{"player": l["player"], **d} for l, d in sorted(lines, key=lambda x: -x[1]["fp"])]}
        r["week"] = r["total"] - base_week[pid] if base_week and pid in base_week else None
        r["trend"] = [history[d].get(pid) for d in dates[-30:]]
    # rang d'hier (mouvement au classement)
    if len(dates) >= 2:
        y = history[dates[-2]]
        order_y = sorted(y, key=lambda k: -y[k])
        for r in rows:
            pid = r["participant"]["id"]
            r["rankMove"] = (order_y.index(pid) + 1 - r["rank"]) if pid in order_y else 0
    playoff_rows = scoring.standings(pool, players, playoff_stats, None, use_moves="active") if pool["rules"].get("playoffs") and playoff_stats else []
    return {"rows": rows, "playoffRows": playoff_rows, "trophies": scoring.trophies(rows),
            "flags": flags(pool, players, stats, cur_teams), "history": history, "phist": phist, "hot": fire, "cold": ice, "dates": dates[-30:], "today": today,
            "best_day": max(((r["participant"]["name"], r["yesterday"]["fp"]) for r in rows), key=lambda x: x[1]) if rows and any(r["yesterday"]["fp"] for r in rows) else None}
