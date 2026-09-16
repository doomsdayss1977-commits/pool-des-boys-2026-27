"""Page web autonome des résultats du pool (HTML unique, CSS inline, logos depuis assets.nhle.com)."""
import time
from html import escape as esc

LOGO = "https://assets.nhle.com/logos/nhl/svg/{abbr}_light.svg"
POS_FR = {"F": "Attaquant", "D": "Défenseur", "G": "Gardien"}

CSS = """
:root{--bg:#070B14;--panel:#111A2E;--panel2:#0D1424;--line:#24314F;--ice:#E8EEF7;--muted:#8A98B8;--gold:#F1D77A;--gold2:#C9A227;--green:#2FBF71;--red:#FF7A8A;--blue:#3A86FF}
[data-theme=light]{--bg:#F2F4F8;--panel:#FFFFFF;--panel2:#F7F8FB;--line:#D6DCE8;--ice:#111827;--muted:#5B6678;--gold:#8A6A00;--gold2:#B8860B;--green:#1B8F52;--red:#C0273D}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ice);font:15px/1.45 "Segoe UI",system-ui,-apple-system,sans-serif;transition:background .2s}
.wrap{max-width:1100px;margin:0 auto;padding:22px 16px 60px}
h1,h2,h3{font-family:Bahnschrift,"Arial Narrow",Impact,sans-serif;letter-spacing:2px;text-transform:uppercase;margin:0}
h1{font-size:38px;line-height:1.1}h2{font-size:20px;color:var(--gold);margin:34px 0 12px}h3{font-size:18px}
.sub{color:var(--muted);margin:6px 0 0}
.top{display:flex;align-items:flex-start;gap:12px}.top .sp{flex:1}
.btn{border:1px solid var(--line);background:var(--panel);color:var(--ice);border-radius:8px;padding:6px 10px;cursor:pointer;font:inherit;font-size:13px}
.card{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);border-radius:14px;padding:16px 18px;box-shadow:0 10px 30px rgba(0,0,0,.25)}
.podium{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}
.pod{border-radius:14px;padding:16px 10px;text-align:center;border:1px solid var(--line);background:linear-gradient(160deg,var(--c1,#1B2745),#0B1222 80%);color:#fff}
.pod.p1{box-shadow:0 0 0 2px #C9A227,0 20px 40px rgba(0,0,0,.4)}
.pod .r{font-family:Bahnschrift,"Arial Narrow",sans-serif;font-size:12px;letter-spacing:3px;color:#F1D77A}
.pod .n{font-family:Bahnschrift,"Arial Narrow",sans-serif;font-size:24px;letter-spacing:1px;margin:6px 0 2px}
.pod .t{font-family:Bahnschrift,"Arial Narrow",sans-serif;font-size:36px;font-weight:700}.pod .t small{font-size:12px;color:#B9C3D6;letter-spacing:2px}
.logo{width:34px;height:34px;vertical-align:middle;filter:drop-shadow(0 2px 3px rgba(0,0,0,.6))}.logo.lg{width:72px;height:72px}.logo.sm{width:20px;height:20px}
table{width:100%;border-collapse:collapse;font-size:14px}th{text-align:left;padding:9px 10px;color:var(--muted);font-size:11px;letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid var(--line)}
td{padding:9px 10px;border-bottom:1px solid var(--line)}.num{text-align:right;font-variant-numeric:tabular-nums}
.tot{font-family:Bahnschrift,"Arial Narrow",sans-serif;font-size:20px;color:var(--gold)}.rk{font-family:Bahnschrift,"Arial Narrow",sans-serif;font-size:18px;width:36px}
.dot{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:8px;vertical-align:middle}
.tag{display:inline-block;padding:1px 7px;border-radius:6px;font-size:11px;font-weight:700;letter-spacing:1px}
.F{background:rgba(58,134,255,.2);color:#3A86FF}.D{background:rgba(47,191,113,.2);color:var(--green)}.G{background:rgba(201,162,39,.25);color:var(--gold)}
.up{color:var(--green);font-size:12px}.down{color:var(--red);font-size:12px}
.flag{display:inline-block;font-size:11px;padding:1px 6px;border-radius:6px;margin-left:6px;background:rgba(255,122,138,.15);color:var(--red)}
.flag.tr{background:rgba(58,134,255,.15);color:var(--blue)}.flag.new{background:rgba(47,191,113,.15);color:var(--green)}
tr.gone td{opacity:.45;text-decoration:line-through}
.roster{margin-top:14px;scroll-margin-top:12px}.roster .head{display:flex;align-items:center;gap:12px;margin-bottom:8px;flex-wrap:wrap}.roster .head .meta{color:var(--muted);font-size:13px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.troph{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.tro{border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:var(--panel2)}
.tro .tn{font-family:Bahnschrift,"Arial Narrow",sans-serif;letter-spacing:2px;color:var(--gold);font-size:13px}
.tro .tp{font-size:17px;font-weight:600;margin:4px 0 0}.tro .td{color:var(--muted);font-size:12px}
.yest{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
.ycard{border:1px solid var(--line);border-radius:12px;padding:10px 12px;background:var(--panel2)}
.ycard b.fp{font-family:Bahnschrift,"Arial Narrow",sans-serif;font-size:22px;float:right;color:var(--gold)}
.ycard ul{margin:6px 0 0;padding-left:16px;font-size:13px;color:var(--muted)}
.chart{width:100%;height:260px}
.legend{display:flex;flex-wrap:wrap;gap:10px;font-size:13px;margin-top:6px}.legend span i{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:5px;vertical-align:middle}
.hof{display:flex;flex-wrap:wrap;gap:10px}.hof .h{border:1px solid var(--gold2);border-radius:12px;padding:10px 14px;background:var(--panel2);text-align:center}
.hof .h b{font-family:Bahnschrift,"Arial Narrow",sans-serif;font-size:18px;display:block}
.moves li{margin:4px 0;font-size:14px}
.muted{color:var(--muted)}.foot{margin-top:40px;color:var(--muted);font-size:12px;text-align:center}
@media(max-width:640px){.podium{grid-template-columns:1fr}h1{font-size:28px}td,th{padding:7px 6px}.hide-sm{display:none}.grid2{grid-template-columns:1fr}}
"""

JS = """
(function(){var k='pool-theme',t=localStorage.getItem(k);if(t)document.documentElement.dataset.theme=t;
document.getElementById('theme').onclick=function(){var c=document.documentElement.dataset.theme==='light'?'':'light';
document.documentElement.dataset.theme=c;localStorage.setItem(k,c);};
if(location.hash){var e=document.getElementById(location.hash.slice(1));if(e)e.scrollIntoView();}})();
"""


def _fmt(v):
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return f"{v:g}" if isinstance(v, float) else v


def _signed(v):
    v = _fmt(v)
    return f"+{v}" if isinstance(v, (int, float)) and v > 0 else str(v)


def _season(sid):
    s = str(sid)
    return f"{s[:4]}-{s[6:]}"


def _chart(rows, dates):
    """Courbe SVG des totaux (30 derniers jours) par participant."""
    if len(dates) < 2:
        return '<p class="muted">La courbe apparaîtra après quelques jours de saison.</p>'
    W, H, L, B = 1000, 260, 40, 24
    vals = [v for r in rows for v in r["trend"] if v is not None]
    mx, mn = max(vals), min(vals)
    span = max(10, (mx - mn) * 1.15)
    lo = max(0, mn - (span - (mx - mn)) / 2)
    n = len(dates)
    x = lambda i: L + i * (W - L - 10) / (n - 1)
    y = lambda v: B + (H - 2 * B) * (1 - (v - lo) / span)
    grid = "".join(f'<line x1="{L}" x2="{W}" y1="{y(lo + span * k / 4):.0f}" y2="{y(lo + span * k / 4):.0f}" stroke="currentColor" opacity=".12"/><text x="0" y="{y(lo + span * k / 4) + 4:.0f}" font-size="11" fill="currentColor" opacity=".6">{lo + span * k / 4:.0f}</text>' for k in range(5))
    lines = ""
    for r in rows:
        pts = [(x(i), y(v)) for i, v in enumerate(r["trend"]) if v is not None]
        if len(pts) < 2:
            continue
        d = "M" + " L".join(f"{px:.0f},{py:.0f}" for px, py in pts)
        lines += f'<path d="{d}" fill="none" stroke="{r["participant"]["color"]}" stroke-width="3" stroke-linejoin="round"/>'
        lines += f'<circle cx="{pts[-1][0]:.0f}" cy="{pts[-1][1]:.0f}" r="4" fill="{r["participant"]["color"]}"/>'
    labels = f'<text x="{L}" y="{H - 4}" font-size="11" fill="currentColor" opacity=".6">{dates[0]}</text><text x="{W}" y="{H - 4}" font-size="11" text-anchor="end" fill="currentColor" opacity=".6">{dates[-1]}</text>'
    legend = "".join(f'<span><i style="background:{r["participant"]["color"]}"></i>{esc(r["participant"]["name"])}</span>' for r in rows)
    return f'<svg class="chart" viewBox="0 0 {W} {H}" preserveAspectRatio="none">{grid}{lines}{labels}</svg><div class="legend">{legend}</div>'


def build_html(pool, res, teams_by_abbr, updated_at, hall_of_fame=None):
    rows, flags = res["rows"], res.get("flags", {})
    pts = pool["rules"]["points"]
    season = _season(pool["rules"]["season"])
    mx = max(1, *[r["total"] for r in rows]) if rows else 1
    team = lambda ab: teams_by_abbr.get(ab, {"nameFr": ab, "short": ab, "colors": ["#1B2745"]})
    logo = lambda ab, cls="logo": f'<img class="{cls}" src="{LOGO.format(abbr=ab)}" alt="{ab}" loading="lazy">'
    pname = lambda pl: f"{esc(pl['first'])} {esc(pl['last'])}"

    def pod(i):
        if i >= len(rows):
            return "<div></div>"
        x = rows[i]; t = team(x["participant"]["team"])
        return (f'<div class="pod p{i+1}" style="--c1:{t["colors"][0]}"><div class="r">{["1RE PLACE","2E PLACE","3E PLACE"][i]}</div>'
                f'{logo(x["participant"]["team"], "logo lg")}<div class="n">{esc(x["participant"]["name"])}</div>'
                f'<div class="t">{_fmt(x["total"])} <small>PTS</small></div></div>')

    def move_badge(r):
        m = r.get("rankMove") or 0
        return f' <span class="up">▲{m}</span>' if m > 0 else (f' <span class="down">▼{-m}</span>' if m < 0 else "")

    stand = "".join(
        f'<tr><td class="rk">{x["rank"]}{move_badge(x)}</td><td><a href="#p-{x["participant"]["id"]}" style="color:inherit;text-decoration:none"><span class="dot" style="background:{x["participant"]["color"]}"></span><b>{esc(x["participant"]["name"])}</b></a></td>'
        f'<td>{logo(x["participant"]["team"], "logo sm")} {esc(team(x["participant"]["team"])["short"])} '
        f'<span class="muted hide-sm">{f"{x['teamRow']['wins']}-{x['teamRow']['losses']}-{x['teamRow']['otl']}" if x.get("teamRow") else ""}</span></td>'
        f'<td class="num">{_signed(x["yesterday"]["fp"])}</td><td class="num hide-sm">{_signed(x["week"]) if x.get("week") is not None else "–"}</td>'
        f'<td class="num hide-sm">{_fmt(x["teamPts"])}</td><td class="num tot">{_fmt(x["total"])}</td>'
        f'<td class="hide-sm" style="width:18%"><div style="height:6px;border-radius:3px;background:rgba(128,128,128,.2);overflow:hidden"><i style="display:block;height:100%;width:{100 * x["total"] / mx:.0f}%;background:linear-gradient(90deg,#3A86FF,#C9A227)"></i></div></td></tr>'
        for x in rows)

    def flag_html(pl, l):
        f = flags.get(str(pl["id"]), {})
        h = ""
        if f.get("traded"):
            h += f'<span class="flag tr" title="Joue maintenant pour {f["traded"]}">→ {f["traded"]}</span>'
        if f.get("missed"):
            h += f'<span class="flag" title="Matchs de son équipe non joués">{f["missed"]} matchs manqués</span>'
        if l.get("since"):
            h += f'<span class="flag new">{"échange" if l.get("via") == "trade" else "remplaçant"} · {l["since"]}</span>'
        return h

    def roster(x):
        p = x["participant"]; t = team(p["team"]); tr = x.get("teamRow") or {}
        lines = ""
        for l in x["lines"]:
            pl, s = l["player"], l["stat"] or {}
            g = pl["pos"] == "G"
            lines += (f'<tr class="{"gone" if l["gone"] else ""}"><td class="muted hide-sm">{l["round"] or "–"}</td><td><b>{pname(pl)}</b>{"" if l["gone"] else flag_html(pl, l)}{f" <span class=muted>(parti le {l["gone"]})</span>" if l["gone"] else ""}</td>'
                      f'<td><span class="tag {pl["pos"]}">{pl["pos"]}</span></td><td>{logo(s.get("team") or pl["team"], "logo sm")}</td>'
                      f'<td class="num hide-sm">{s.get("gp", 0)}</td><td class="num">{"–" if g else s.get("g", 0)}</td><td class="num">{"–" if g else s.get("a", 0)}</td>'
                      f'<td class="num">{s.get("w", 0) if g else "–"}</td><td class="num">{s.get("so", 0) if g else "–"}</td><td class="num tot" style="font-size:16px">{_fmt(l["fp"])}</td></tr>')
        return (f'<div class="card roster" id="p-{p["id"]}"><div class="head">{logo(p["team"])}<div><h3 style="color:{p["color"]}">{x["rank"]}. {esc(p["name"])}</h3>'
                f'<div class="meta">{esc(t["nameFr"])}{f" · {tr['wins']}-{tr['losses']}-{tr['otl']}" if tr else ""} · victoires × {_fmt(pts["teamWin"])} = {_fmt(x["teamPts"])} pts · hier {_signed(x["yesterday"]["fp"])}</div></div>'
                f'<div style="margin-left:auto" class="tot">{_fmt(x["total"])} pts</div></div>'
                f'<table><thead><tr><th class="hide-sm">R</th><th>Joueur</th><th>Pos</th><th>Éq.</th><th class="num hide-sm">PJ</th><th class="num">B</th><th class="num">A</th><th class="num">V</th><th class="num">BL</th><th class="num">Pts</th></tr></thead>'
                f'<tbody>{lines}</tbody></table></div>')

    def yesterday():
        cards = ""
        for x in rows:
            y = x["yesterday"]
            if not y["lines"]:
                continue
            items = "".join(f'<li>{pname(d["player"])} : {_signed(d["fp"])} <span class="muted">({", ".join(f"{v}{k}" for k, v in (("B", d["line"]["g"]), ("A", d["line"]["a"]), ("V", d["line"]["w"]), ("BL", d["line"]["so"])) if v)})</span></li>' for d in y["lines"][:5])
            cards += f'<div class="ycard"><b class="fp">{_signed(y["fp"])}</b><b style="color:{x["participant"]["color"]}">{esc(x["participant"]["name"])}</b><ul>{items}</ul></div>'
        if not cards:
            return '<p class="muted">Aucun point marqué depuis la dernière mise à jour.</p>'
        best = res.get("best_day")
        return (f'<p class="muted" style="margin:0 0 10px">🔥 Journée du jour : <b>{esc(best[0])}</b> ({_signed(best[1])})</p>' if best else "") + f'<div class="yest">{cards}</div>'

    troph = "".join(f'<div class="tro"><div class="tn">{esc(t["name"])}</div><div class="tp">{esc(t["player"])} <span class="muted">({t["team"]})</span></div><div class="td">{esc(t["desc"])} · {_fmt(t["value"])} pts · <span style="color:{t["color"]}">{esc(t["who"])}</span>{f" · {esc(t['extra'])}" if t.get("extra") else ""}</div></div>' for t in res.get("trophies", []))

    players = pool.get("players") or {}
    def pl_name(i):
        pl = players.get(str(i)) or {}
        return f"{pl.get('first', '')} {pl.get('last', i)}".strip()
    part_name = {p["id"]: p["name"] for p in pool["participants"]}
    moves = ""
    for mv in reversed(pool.get("moves", [])):
        if mv["type"] == "replace":
            moves += f'<li>{mv["date"]} — <b>{esc(part_name.get(mv["participantId"], "?"))}</b> remplace {esc(pl_name(mv["out"]["playerId"]))} par <b>{esc(pl_name(mv["in"]["playerId"]))}</b></li>'
        else:
            a, b = mv["a"], mv["b"]
            moves += f'<li>{mv["date"]} — Échange : <b>{esc(part_name.get(a["participantId"], "?"))}</b> cède {esc(", ".join(pl_name(g["playerId"]) for g in a["gives"]))} à <b>{esc(part_name.get(b["participantId"], "?"))}</b> contre {esc(", ".join(pl_name(g["playerId"]) for g in b["gives"]))}</li>'

    playoff = ""
    if res.get("playoffRows"):
        playoff = '<h2>Séries éliminatoires</h2><div class="card" style="padding:0;overflow:hidden"><table><thead><tr><th></th><th>Participant</th><th class="num">Pts séries</th></tr></thead><tbody>' + "".join(
            f'<tr><td class="rk">{x["rank"]}</td><td><span class="dot" style="background:{x["participant"]["color"]}"></span><b>{esc(x["participant"]["name"])}</b></td><td class="num tot">{_fmt(x["playerPts"])}</td></tr>' for x in res["playoffRows"]) + "</tbody></table></div>"

    hof = "".join(f'<div class="h"><span class="muted">{_season(h["season"])}</span><b>🏆 {esc(h["name"])}</b><span class="muted">{esc(h["pool"])} · {_fmt(h["total"])} pts</span></div>' for h in (hall_of_fame or []))

    bareme = " · ".join(f"{lbl} {_fmt(pts[k])}" for k, lbl in (("goal", "but"), ("assist", "passe"), ("teamWin", "victoire d'équipe"), ("goalieWin", "victoire du gardien"), ("shutout", "blanchissage")))
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(pool["name"])} — Pool LNH {season}</title><style>{CSS}</style></head><body><div class="wrap">
<div class="top"><div class="sp"><h1>{esc(pool["name"])}</h1><p class="sub">Pool fantasy LNH · saison {season} · stats au {esc(updated_at or "—")} · mise à jour automatique chaque matin</p></div><button class="btn" id="theme">☀️ / 🌙</button></div>
<div class="podium">{pod(1)}{pod(0)}{pod(2)}</div>
<h2>Classement</h2><div class="card" style="padding:0;overflow:hidden"><table><thead><tr><th></th><th>Participant</th><th>Équipe LNH</th><th class="num">Hier</th><th class="num hide-sm">7 jours</th><th class="num hide-sm">Pts équipe</th><th class="num">Total</th><th class="hide-sm"></th></tr></thead><tbody>{stand}</tbody></table></div>
<h2>Tendance (30 jours)</h2><div class="card">{_chart(rows, res.get("dates", []))}</div>
<h2>Points d'hier</h2>{yesterday()}
{f'<h2>Trophées du pool</h2><div class="troph">{troph}</div>' if troph else ""}
{playoff}
<h2>Alignements</h2>{"".join(roster(x) for x in rows)}
{f'<h2>Transactions</h2><div class="card"><ul class="moves">{moves}</ul></div>' if moves else ""}
{f'<h2>Mur des champions</h2><div class="hof">{hof}</div>' if hof else ""}
<p class="foot">Barème : {bareme}. Remplacements permis : {pool["rules"].get("maxReplacements", 2)} par participant{f" · date limite des transactions : {pool['rules']['tradeDeadline']}" if pool["rules"].get("tradeDeadline") else ""}. Données : NHL.com. Généré par Repêchage Fantasy LNH.</p></div>
<script>{JS}</script></body></html>"""
