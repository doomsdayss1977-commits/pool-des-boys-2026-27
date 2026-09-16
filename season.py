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


def compute(pool, players, stats, cur_teams, playoff_stats, history, prev, today=None):
    """Retourne tout ce que la page et l'app affichent.
    history = {date: {participantId: total}} (tendance) ; prev = {"date", "players"} = stats de la dernière passe (points d'hier)."""
    today = today or dt.date.today().isoformat()
    rows = scoring.standings(pool, players, stats, cur_teams)
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
            "flags": flags(pool, players, stats, cur_teams), "history": history, "dates": dates[-30:], "today": today,
            "best_day": max(((r["participant"]["name"], r["yesterday"]["fp"]) for r in rows), key=lambda x: x[1]) if rows and any(r["yesterday"]["fp"] for r in rows) else None}
