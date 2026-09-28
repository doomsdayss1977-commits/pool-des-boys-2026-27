"""Exécuté par GitHub Actions dans le dépôt du pool : stats LNH du jour -> index.html (+ historique, Discord).
Si la LNH ne répond pas pour toutes les équipes, on échoue SANS rien écrire : la page d'hier reste en ligne."""
import json
import os
import sys
import time
from pathlib import Path

import requests

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
    sea = pool["rules"]["season"]
    abbrs = [t["abbr"] for t in pool["teams"]]
    stats = {str(k): v for k, v in nhl.all_club_stats(sea, abbrs, force=True, strict=True).items()}
    teams = [t for t in nhl.standings("now", force=True) if t["season"] == sea]
    playoffs = {str(k): v for k, v in nhl.all_club_stats(sea, abbrs, force=True, game_type=3).items()} if pool["rules"].get("playoffs") else {}
    today = today or time.strftime("%Y-%m-%d", time.gmtime())
    res = season.compute(pool, pool["players"], stats, teams, playoffs, history, prev, today)
    updated = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    html = web_export.build_html(pool, res, {t["abbr"]: t for t in pool["teams"]}, updated, pool.get("hallOfFame", []))
    # Tout est calculé : on écrit seulement maintenant.
    (root / "index.html").write_text(html, "utf-8")
    (root / "history.json").write_text(json.dumps(res["history"]), "utf-8")
    if not prev or prev.get("date") != today:
        (root / "stats_prev.json").write_text(json.dumps({"date": today, "players": stats}), "utf-8")
    print(f"{len(stats)} joueurs, {len(teams)} équipes, {updated}")
    return pool, res, today


def discord(pool, res, today):
    hook = os.environ.get("DISCORD_WEBHOOK")
    if not hook or not any(r["yesterday"]["fp"] for r in res["rows"]):
        return
    url = os.environ.get("PAGE_URL", "")
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
    try:
        requests.post(hook, json={"content": "\n".join(lines)[:1900]}, timeout=20)
    except requests.RequestException as e:
        print("Discord :", e)


if __name__ == "__main__":
    try:
        discord(*run(NHL(".cache", ttl_hours=0)))
    except Exception as e:
        print(f"Mise à jour annulée, page d'hier conservée : {e}")
        sys.exit(1)
