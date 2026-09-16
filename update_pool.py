"""Exécuté par GitHub Actions dans le dépôt du pool : stats LNH du jour -> index.html (+ historique, Discord)."""
import json
import os
import time
from pathlib import Path

import requests

import season
import web_export
from nhl_api import NHL


def load(path, default):
    return json.loads(Path(path).read_text("utf-8")) if Path(path).exists() else default


pool = load("pool.json", None)
history = load("history.json", {})
prev = load("stats_prev.json", None)
nhl = NHL(".cache", ttl_hours=0)
sea = pool["rules"]["season"]
abbrs = [t["abbr"] for t in pool["teams"]]
stats = {str(k): v for k, v in nhl.all_club_stats(sea, abbrs, force=True).items()}
teams = [t for t in nhl.standings("now", force=True) if t["season"] == sea]
playoffs = {str(k): v for k, v in nhl.all_club_stats(sea, abbrs, force=True, game_type=3).items()} if pool["rules"].get("playoffs") else {}
today = time.strftime("%Y-%m-%d", time.gmtime())
res = season.compute(pool, pool["players"], stats, teams, playoffs, history, prev, today)
updated = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
Path("index.html").write_text(web_export.build_html(pool, res, {t["abbr"]: t for t in pool["teams"]}, updated, pool.get("hallOfFame", [])), "utf-8")
Path("history.json").write_text(json.dumps(res["history"]), "utf-8")
if not prev or prev.get("date") != today:
    Path("stats_prev.json").write_text(json.dumps({"date": today, "players": stats}), "utf-8")
print(f"{len(stats)} joueurs, {len(teams)} équipes, {updated}")

hook = os.environ.get("DISCORD_WEBHOOK")
if hook and any(r["yesterday"]["fp"] for r in res["rows"]):
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
