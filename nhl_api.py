"""Client minimal pour l'API publique de la LNH (api-web.nhle.com) avec cache disque."""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

BASE = "https://api-web.nhle.com/v1"
LOGO = "https://assets.nhle.com/logos/nhl/svg/{abbr}_light.svg"

# Couleurs officielles (primaire, secondaire) par équipe — pour la roue et les cartes.
TEAM_COLORS = {
    "ANA": ("#F47A38", "#B9975B"), "BOS": ("#FFB81C", "#000000"), "BUF": ("#003087", "#FFB81C"),
    "CGY": ("#D2001C", "#FAAF19"), "CAR": ("#CE1126", "#A4A9AD"), "CHI": ("#CF0A2C", "#000000"),
    "COL": ("#6F263D", "#236192"), "CBJ": ("#002654", "#CE1126"), "DAL": ("#006847", "#8F8F8C"),
    "DET": ("#CE1126", "#FFFFFF"), "EDM": ("#041E42", "#FF4C00"), "FLA": ("#C8102E", "#041E42"),
    "LAK": ("#111111", "#A2AAAD"), "MIN": ("#154734", "#A6192E"), "MTL": ("#AF1E2D", "#192168"),
    "NSH": ("#FFB81C", "#041E42"), "NJD": ("#CE1126", "#000000"), "NYI": ("#00539B", "#F47D30"),
    "NYR": ("#0038A8", "#CE1126"), "OTT": ("#DA1A32", "#B79257"), "PHI": ("#F74902", "#000000"),
    "PIT": ("#FCB514", "#000000"), "SJS": ("#006D75", "#EA7200"), "SEA": ("#001628", "#99D9D9"),
    "STL": ("#002F87", "#FCB514"), "TBL": ("#002868", "#FFFFFF"), "TOR": ("#00205B", "#FFFFFF"),
    "UTA": ("#6CACE4", "#010101"), "VAN": ("#00205B", "#00843D"), "VGK": ("#B4975A", "#333F42"),
    "WSH": ("#C8102E", "#041E42"), "WPG": ("#041E42", "#004C97"),
}

NOMS_FR = {
    "ANA": "Ducks d'Anaheim", "BOS": "Bruins de Boston", "BUF": "Sabres de Buffalo",
    "CGY": "Flames de Calgary", "CAR": "Hurricanes de la Caroline", "CHI": "Blackhawks de Chicago",
    "COL": "Avalanche du Colorado", "CBJ": "Blue Jackets de Columbus", "DAL": "Stars de Dallas",
    "DET": "Red Wings de Détroit", "EDM": "Oilers d'Edmonton", "FLA": "Panthers de la Floride",
    "LAK": "Kings de Los Angeles", "MIN": "Wild du Minnesota", "MTL": "Canadiens de Montréal",
    "NSH": "Predators de Nashville", "NJD": "Devils du New Jersey", "NYI": "Islanders de New York",
    "NYR": "Rangers de New York", "OTT": "Sénateurs d'Ottawa", "PHI": "Flyers de Philadelphie",
    "PIT": "Penguins de Pittsburgh", "SJS": "Sharks de San Jose", "SEA": "Kraken de Seattle",
    "STL": "Blues de St. Louis", "TBL": "Lightning de Tampa Bay", "TOR": "Maple Leafs de Toronto",
    "UTA": "Mammoth de l'Utah", "VAN": "Canucks de Vancouver", "VGK": "Golden Knights de Vegas",
    "WSH": "Capitals de Washington", "WPG": "Jets de Winnipeg",
}


def _s():
    s = requests.Session()
    s.headers["User-Agent"] = "HockeyDraft/1.0"
    return s


class NHL:
    def __init__(self, cache_dir: Path, ttl_hours: float = 6):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_hours * 3600
        self.s = _s()

    def _get(self, path, key, force=False):
        f = self.cache / (key + ".json")
        if not force and f.exists() and time.time() - f.stat().st_mtime < self.ttl:
            return json.loads(f.read_text("utf-8"))
        r = self.s.get(f"{BASE}/{path}", timeout=20)
        r.raise_for_status()
        data = r.json()
        f.write_text(json.dumps(data), "utf-8")
        return data

    def standings(self, date="now", force=False):
        """Classement à une date (YYYY-MM-DD ou 'now'), trié du 1er au dernier."""
        raw = self._get(f"standings/{date}", f"standings_{date}", force)["standings"]
        out = []
        for t in raw:
            ab = t["teamAbbrev"]["default"]
            out.append({
                "abbr": ab,
                "name": t["teamName"]["default"],
                "nameFr": NOMS_FR.get(ab, t["teamName"]["default"]),
                "short": t["teamCommonName"]["default"],
                "rank": t["leagueSequence"],
                "points": t["points"], "wins": t["wins"], "losses": t["losses"], "otl": t["otLosses"],
                "gp": t["gamesPlayed"],
                "conf": t["conferenceAbbrev"], "div": t["divisionAbbrev"],
                "season": t["seasonId"],
                "colors": TEAM_COLORS.get(ab, ("#444444", "#999999")),
            })
        out.sort(key=lambda x: x["rank"])
        return out

    def roster(self, abbr, season, force=False):
        raw = self._get(f"roster/{abbr}/{season}", f"roster_{abbr}_{season}", force)
        players = []
        for grp, pos in (("forwards", "F"), ("defensemen", "D"), ("goalies", "G")):
            for p in raw.get(grp, []):
                players.append({
                    "id": p["id"],
                    "first": p["firstName"]["default"], "last": p["lastName"]["default"],
                    "pos": pos, "posCode": p.get("positionCode", pos),
                    "num": p.get("sweaterNumber"), "team": abbr,
                    "headshot": p.get("headshot"),
                    "birth": p.get("birthDate"),
                })
        return players

    def club_stats(self, abbr, season, force=False, game_type=2):
        """Stats d'une équipe pour tous ses joueurs (gameType 2 = saison, 3 = séries)."""
        suffix = "" if game_type == 2 else f"_g{game_type}"
        raw = self._get(f"club-stats/{abbr}/{season}/{game_type}", f"clubstats_{abbr}_{season}{suffix}", force)
        out = {}
        for p in raw.get("skaters", []):
            out[p["playerId"]] = {"team": abbr,
                "gp": p["gamesPlayed"], "g": p["goals"], "a": p["assists"], "pts": p["points"],
                "pm": p.get("plusMinus", 0), "ppg": p.get("powerPlayGoals", 0),
                "shg": p.get("shorthandedGoals", 0), "gwg": p.get("gameWinningGoals", 0),
                "otg": p.get("overtimeGoals", 0), "pim": p.get("penaltyMinutes", 0),
                "shots": p.get("shots", 0),
            }
        for p in raw.get("goalies", []):
            out[p["playerId"]] = {"team": abbr,
                "gp": p["gamesPlayed"], "gs": p.get("gamesStarted", 0), "w": p["wins"], "l": p["losses"],
                "otl": p.get("overtimeLosses", 0), "so": p.get("shutouts", 0), "gaa": p.get("goalsAgainstAverage"),
                "svp": p.get("savePercentage"), "g": p.get("goals", 0), "a": p.get("assists", 0),
                "saves": p.get("saves", 0),
            }
        return out

    def _each_team(self, fn, abbrs, progress):
        """Appelle fn(abbr) pour chaque équipe en parallèle (I/O réseau) ; une équipe injoignable est ignorée."""
        def one(ab):
            try:
                return fn(ab)
            except requests.RequestException:
                return None
        results = []
        with ThreadPoolExecutor(max_workers=8) as ex:
            for i, r in enumerate(ex.map(one, abbrs), 1):
                results.append(r)
                if progress:
                    progress(i, len(abbrs))
        return [r for r in results if r is not None]

    def all_rosters(self, season, abbrs, force=False, progress=None):
        return [p for team in self._each_team(lambda ab: self.roster(ab, season, force), abbrs, progress) for p in team]

    def all_club_stats(self, season, abbrs, force=False, progress=None, game_type=2):
        """Stats de tous les joueurs ; un joueur échangé (présent chez deux équipes) voit ses compteurs additionnés."""
        stats = {}
        for team in self._each_team(lambda ab: self.club_stats(ab, season, force, game_type), abbrs, progress):
            for pid, st in team.items():
                if pid in stats:
                    old = stats[pid]
                    merged = {k: (old.get(k, 0) or 0) + (v or 0) if isinstance(v, (int, float)) and k not in ("gaa", "svp") else v
                              for k, v in st.items()}
                    merged["teams"] = old.get("teams", [old["team"]]) + [st["team"]]
                    merged["team"] = st["team"]
                    stats[pid] = merged
                else:
                    stats[pid] = st
        return stats

    def logo_svg(self, abbr):
        r = self.s.get(LOGO.format(abbr=abbr), timeout=20)
        r.raise_for_status()
        return r.text


def season_ids(today=None):
    """(saison précédente, saison en cours) en format 20252026 selon la date (bascule le 1er juillet)."""
    import datetime as dt
    today = today or dt.date.today()
    y = today.year if today.month >= 7 else today.year - 1
    return int(f"{y-1}{y}"), int(f"{y}{y+1}")
