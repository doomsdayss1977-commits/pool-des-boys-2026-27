"""Exécuté par GitHub Actions dans le dépôt du pool : stats LNH du jour -> index.html (+ historique, Discord).
Si la LNH ne répond pas pour toutes les équipes, on échoue SANS rien écrire : la page d'hier reste en ligne."""
import datetime as dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import requests

import draft
import season
import web_export
from nhl_api import NHL


def load(path, default):
    return json.loads(Path(path).read_text("utf-8")) if Path(path).exists() else default


def run(nhl, root=".", today=None):
    root = Path(root)
    pool = load(root / "pool.json", None)
    history = load(root / "history.json", {})
    prev = load(root / "stats_prev.json", None)
    phist = load(root / "phist.json", {})
    old_flags = load(root / "flags.json", None)
    sea = pool["rules"]["season"]
    abbrs = [t["abbr"] for t in pool["teams"]]
    stats = {str(k): v for k, v in nhl.all_club_stats(sea, abbrs, force=True, strict=True).items()}
    teams = [t for t in nhl.standings("now", force=True) if t["season"] == sea]
    playoffs = {str(k): v for k, v in nhl.all_club_stats(sea, abbrs, force=True, game_type=3).items()} if pool["rules"].get("playoffs") else {}
    try:
        week = nhl.week_games(force=True)
    except Exception:
        week = None
    # Journée de hockey : commence à 10h UTC (6h au Québec), pour qu'une soirée de matchs reste dans la même journée.
    today = today or (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=10)).date().isoformat()
    rolled = not prev or prev.get("date") != today
    if rolled:   # 1er passage de la journée : la base du jour = stats actuelles, on garde celle de la veille
        prev = {"date": today, "players": stats, "before": (prev or {}).get("players")}
    live = stats != prev["players"]   # des matchs de ce soir sont terminés → points de la soirée, sinon ceux d'hier
    base = prev["players"] if live else prev.get("before")
    res = season.compute(pool, pool["players"], stats, teams, playoffs, history, base and {"date": None, "players": base}, today, phist, week)
    res["live"] = live
    res["alerts"] = alerts(pool, res["flags"], old_flags)
    updated = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    html = web_export.build_html(pool, res, {t["abbr"]: t for t in pool["teams"]}, updated, pool.get("hallOfFame", []))
    sha = hashlib.sha1(html.replace(updated, "").encode()).hexdigest()   # l'heure seule ne compte pas comme un changement
    if not rolled and sha == load(root / "page.sha.json", None):
        print(f"Aucun nouveau point ({updated}) : rien publié")
        return pool, None, today, False
    # Tout est calculé : on écrit seulement maintenant.
    (root / "index.html").write_text(html, "utf-8")
    (root / "page.sha.json").write_text(json.dumps(sha), "utf-8")
    (root / "history.json").write_text(json.dumps(res["history"]), "utf-8")
    (root / "phist.json").write_text(json.dumps(res["phist"]), "utf-8")
    (root / "flags.json").write_text(json.dumps(res["flags"]), "utf-8")
    if rolled:
        (root / "stats_prev.json").write_text(json.dumps(prev), "utf-8")
    print(f"{len(stats)} joueurs, {len(teams)} équipes, {updated}")
    return pool, res, today, rolled


def alerts(pool, flags, old):
    """Nouveaux signaux depuis la veille : joueur échangé, ou absent 3 matchs et plus (blessure, LAH…)."""
    if old is None:   # première passe : on ne réveille pas tout le monde avec l'historique
        return []
    rosters = draft.rosters(pool)
    owner = {str(l["playerId"]): p for p in pool["participants"] for l in rosters[p["id"]] if "gone" not in l}
    out = []
    for pid, f in flags.items():
        o = old.get(pid, {})
        pl = pool["players"].get(pid)
        if not pl or pid not in owner:
            continue
        who = f"{pl['first']} {pl['last']} ({owner[pid]['name']})"
        if f.get("traded") and f["traded"] != o.get("traded"):
            out.append(f"🔁 {who} joue maintenant pour {f['traded']}")
        if f.get("missed") and not o.get("missed"):
            out.append(f"🚑 {who} a manqué {f['missed']} matchs de son équipe — blessé ou renvoyé ?")
    return out


def _post(hook, text):
    try:
        requests.post(hook, json={"content": text[:1900]}, timeout=20)
    except requests.RequestException as e:
        print("Discord :", e)


def weekly(pool, res, url):
    """Bilan du lundi : gains de la semaine, joueurs en feu / à froid, projection."""
    wk = sorted(res["rows"], key=lambda r: -(r.get("week") or 0))
    msg = [f"📅 **{pool['name']}** — bilan de la semaine"]
    msg += [f"{i}. **{r['participant']['name']}** {r['week'] or 0:+g} pts cette semaine (total {r['total']:g})" for i, r in enumerate(wk, 1)]
    if res.get("hot"):
        msg.append("🔥 En feu : " + ", ".join(f"{h['player']['last']} {h['f7']:+g}" for h in res["hot"][:3]))
    if res.get("cold"):
        msg.append("🧊 À froid : " + ", ".join(f"{h['player']['last']} ({h['gp7']} PJ, 0 pt)" for h in res["cold"][:3]))
    proj = [r for r in res["rows"] if r.get("proj") is not None]
    if proj:
        best = max(proj, key=lambda r: r["proj"])
        msg.append(f"🔮 Projection fin de saison : {best['participant']['name']} ({best['proj']:.0f} pts)")
    return "\n".join(msg + ([url] if url else []))


def discord(pool, res, today, rolled=True):
    hook = os.environ.get("DISCORD_WEBHOOK")
    if not hook or not res:
        return
    url = os.environ.get("PAGE_URL", "")
    if res.get("alerts"):
        _post(hook, f"**{pool['name']}** — alertes\n" + "\n".join(res["alerts"]))
    if not rolled:   # bilans : seulement au 1er passage de la journée, pas aux 20 min du soir
        return
    if dt.date.fromisoformat(today).weekday() == 0 and any(r.get("week") for r in res["rows"]):
        _post(hook, weekly(pool, res, url))
    if not any(r["yesterday"]["fp"] for r in res["rows"]):
        return
    lines = [f"**{pool['name']}** — classement du {today}"]
    for r in res["rows"]:
        mv = r.get("rankMove") or 0
        arrow = " ⬆️" if mv > 0 else (" ⬇️" if mv < 0 else "")
        y = r["yesterday"]["fp"]
        lines.append(f"{r['rank']}. **{r['participant']['name']}** {r['total']:g} pts (hier {y:+g}){arrow}")
    if res.get("best_day"):
        lines.append(f"🔥 Journée du jour : {res['best_day'][0]} (+{res['best_day'][1]:g})")
    if url:
        lines.append(url)
    _post(hook, "\n".join(lines))


if __name__ == "__main__":
    try:
        discord(*run(NHL(".cache", ttl_hours=0)))
    except Exception as e:
        print(f"Mise à jour annulée, page d'hier conservée : {e}")
        sys.exit(1)
