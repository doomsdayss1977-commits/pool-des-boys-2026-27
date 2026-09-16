"""Calcul des points fantasy à partir des stats LNH de la saison en cours."""


def skater_points(s, pts):
    if not s:
        return 0
    g, a = s.get("g", 0), s.get("a", 0)
    total = g * pts["goal"] + a * pts["assist"]
    total += s.get("ppg", 0) * pts.get("ppGoal", 0)
    total += s.get("shg", 0) * pts.get("shGoal", 0)
    total += s.get("gwg", 0) * pts.get("gwg", 0)
    total += s.get("otg", 0) * pts.get("otGoal", 0)
    total += s.get("pm", 0) * pts.get("plusMinus", 0)
    return total


def goalie_points(s, pts):
    if not s:
        return 0
    total = s.get("w", 0) * pts["goalieWin"] + s.get("so", 0) * pts["shutout"]
    total += s.get("otl", 0) * pts.get("goalieOtl", 0)
    total += (s.get("g", 0) + s.get("a", 0)) * pts.get("goalieGoalAssist", 0)
    return total


def player_points(player, stat, pts):
    return goalie_points(stat, pts) if player["pos"] == "G" else skater_points(stat, pts)


def team_points(team_row, pts):
    if not team_row:
        return 0
    return team_row.get("wins", 0) * pts["teamWin"] + team_row.get("otl", 0) * pts.get("teamOtl", 0)


def standings(pool, players, stats, cur_teams, use_moves=True):
    """Classement du pool. stats = {playerId: statline}, cur_teams = classement LNH en cours (liste).
    use_moves="active" : alignements actuels mais sans points figés ni baseline (séries éliminatoires)."""
    import draft
    pts = pool["rules"]["points"]
    teams = {t["abbr"]: t for t in cur_teams} if cur_teams else {}
    stats = stats or {}
    rosters = draft.rosters(pool)
    rows = []
    for part in pool["participants"]:
        lines = []
        total = 0
        for l in rosters[part["id"]]:
            if use_moves == "active" and "gone" in l:
                continue
            pl = players[str(l["playerId"])]
            st = stats.get(str(pl["id"]))
            if "gone" in l:
                fp = l.get("frozenFp", 0)
            else:
                fp = player_points(pl, st, pts)
                if l.get("baseline") and use_moves is True:
                    fp -= player_points(pl, l["baseline"], pts)
            total += fp
            lines.append({"player": pl, "stat": st, "fp": fp, "round": l.get("round"), "overall": l.get("overall"),
                          "gone": l.get("gone"), "since": l.get("since"), "via": l.get("via")})
        order = {"F": 0, "D": 1, "G": 2}
        lines.sort(key=lambda l: (l["gone"] is not None, order[l["player"]["pos"]], -l["fp"]))
        trow = teams.get(part["team"])
        tp = team_points(trow, pts)
        total += tp
        rows.append({"participant": part, "lines": lines, "teamRow": trow, "teamPts": tp,
                     "playerPts": total - tp, "total": total})
    rows.sort(key=lambda r: -r["total"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def fp_map(pool, players, stats):
    """{playerId: points fantasy bruts (sans baseline)} pour tous les joueurs ayant des stats — sert à figer les points lors d'une transaction."""
    pts = pool["rules"]["points"]
    return {str(pid): player_points(players[str(pid)], st, pts) for pid, st in (stats or {}).items() if str(pid) in players}


def trophies(rows):
    """Trophées du pool calculés sur les lignes actives des alignements."""
    active = [(r["participant"], l) for r in rows for l in r["lines"] if not l["gone"]]
    if not active or not any(l["fp"] for _, l in active):
        return []
    def best(filt, key=lambda x: x[1]["fp"], reverse=True):
        c = [x for x in active if filt(x)]
        return max(c, key=key) if c else None
    def fmt(x, extra=""):
        p, l = x
        return {"who": p["name"], "color": p["color"], "player": f"{l['player']['first']} {l['player']['last']}",
                "team": l["player"]["team"], "value": l["fp"], "extra": extra}
    out = []
    x = best(lambda x: x[1]["player"]["pos"] != "G")
    if x: out.append({"name": "Art Ross du pool", "desc": "Patineur le plus productif", **fmt(x)})
    x = best(lambda x: x[1]["player"]["pos"] == "D")
    if x: out.append({"name": "Norris du pool", "desc": "Meilleur défenseur", **fmt(x)})
    x = best(lambda x: x[1]["player"]["pos"] == "G")
    if x: out.append({"name": "Vézina du pool", "desc": "Meilleur gardien", **fmt(x)})
    x = best(lambda x: x[1]["round"] and x[1]["round"] >= 4)
    if x: out.append({"name": "Vol de l'année", "desc": "Meilleur joueur repêché à la ronde 4 ou plus", **fmt(x, f"ronde {x[1]['round']}")})
    x = best(lambda x: x[1]["round"] == 1, reverse=False, key=lambda x: -x[1]["fp"])
    if x: out.append({"name": "Pire 1er choix", "desc": "Sélection de 1re ronde la moins productive", **fmt(x)})
    x = best(lambda x: x[1].get("via") in ("replace", "trade"))
    if x: out.append({"name": "Coup de génie", "desc": "Meilleure acquisition en saison", **fmt(x, x[1]["via"] == "trade" and "échange" or "remplacement")})
    return out


def daily_deltas(prev_stats, cur_stats, pool, players):
    """Points gagnés depuis la veille par joueur : {playerId: {fp, line}} — line = stats de la journée (g, a, w, so)."""
    pts = pool["rules"]["points"]
    out = {}
    for pid, st in (cur_stats or {}).items():
        pl = players.get(str(pid))
        if not pl:
            continue
        prev = (prev_stats or {}).get(str(pid)) or {}
        d = {k: st.get(k, 0) - prev.get(k, 0) for k in ("g", "a", "w", "so", "otl", "ppg", "shg", "gwg", "otg", "pm", "gp")}
        fp = player_points(pl, d, pts)
        if fp or d["gp"]:
            out[str(pid)] = {"fp": fp, "line": d}
    return out
