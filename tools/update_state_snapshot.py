import json
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
R32_MAPPING_PATH = DATA_DIR / "r32_third_mapping.json"
STATE_SNAPSHOT_PATH = DATA_DIR / "state_snapshot.json"

ESPN_STANDINGS_API = "https://site.web.api.espn.com/apis/v2/sports/soccer/fifa.world/standings?region=us&lang=en"
ESPN_R32_SCOREBOARD_API = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260628-20260704&limit=200"


def now_ms() -> int:
    return int(time.time() * 1000)


def clean_text(s: Any) -> str:
    return ("" if s is None else str(s)).replace("\xa0", " ").strip()


def safe_int(s: Any) -> Optional[int]:
    if s is None:
        return None
    try:
        text = str(s).replace("+", "").strip()
        return int(float(text))
    except Exception:
        return None


def fetch_url(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


@dataclass
class TeamRow:
    team: str
    pts: Optional[int]
    gd: Optional[int] = None
    gf: Optional[int] = None


TEAM_ZH = {
    "Algeria": "阿尔及利亚",
    "Argentina": "阿根廷",
    "Australia": "澳大利亚",
    "Austria": "奥地利",
    "Belgium": "比利时",
    "Bosnia-Herzegovina": "波黑",
    "Brazil": "巴西",
    "Canada": "加拿大",
    "Cape Verde": "佛得角",
    "Colombia": "哥伦比亚",
    "Congo DR": "刚果（金）",
    "Croatia": "克罗地亚",
    "Curaçao": "库拉索",
    "Czech Republic": "捷克",
    "Czechia": "捷克",
    "Denmark": "丹麦",
    "Ecuador": "厄瓜多尔",
    "Egypt": "埃及",
    "England": "英格兰",
    "France": "法国",
    "Germany": "德国",
    "Ghana": "加纳",
    "Haiti": "海地",
    "Iran": "伊朗",
    "Iraq": "伊拉克",
    "Ivory Coast": "科特迪瓦",
    "Côte d'Ivoire": "科特迪瓦",
    "Japan": "日本",
    "Mexico": "墨西哥",
    "Morocco": "摩洛哥",
    "Netherlands": "荷兰",
    "New Zealand": "新西兰",
    "Norway": "挪威",
    "Panama": "巴拿马",
    "Paraguay": "巴拉圭",
    "Portugal": "葡萄牙",
    "Qatar": "卡塔尔",
    "Saudi Arabia": "沙特阿拉伯",
    "Scotland": "苏格兰",
    "Senegal": "塞内加尔",
    "South Africa": "南非",
    "South Korea": "韩国",
    "Korea Republic": "韩国",
    "Spain": "西班牙",
    "Sweden": "瑞典",
    "Switzerland": "瑞士",
    "Tunisia": "突尼斯",
    "Türkiye": "土耳其",
    "Turkey": "土耳其",
    "United States": "美国",
    "USA": "美国",
    "Uruguay": "乌拉圭",
    "Uzbekistan": "乌兹别克斯坦",
}


def zh_team(name: str) -> str:
    return TEAM_ZH.get(name, name)


def parse_espn_standings(api_text: str) -> Dict[str, List[TeamRow]]:
    payload = json.loads(api_text)
    groups: Dict[str, List[TeamRow]] = {}

    for child in payload.get("children", []) or []:
        name = child.get("name") or child.get("abbreviation") or ""
        match = re.search(r"Group\s+([A-L])", name, flags=re.I)
        if not match:
            continue
        group = match.group(1).upper()
        entries = ((child.get("standings") or {}).get("entries") or [])
        rows: List[TeamRow] = []

        for entry in entries:
            team_obj = entry.get("team") or {}
            team = zh_team(clean_text(team_obj.get("displayName") or team_obj.get("name") or team_obj.get("shortDisplayName") or ""))
            if not team:
                continue

            stats = {str(s.get("name") or s.get("type") or "").lower(): s for s in (entry.get("stats") or [])}

            def stat_int(*names: str) -> Optional[int]:
                for stat_name in names:
                    stat = stats.get(stat_name.lower())
                    if stat is None:
                        continue
                    value = stat.get("value")
                    if value is None:
                        value = stat.get("displayValue")
                    return safe_int(str(value))
                return None

            rows.append(
                TeamRow(
                    team=team,
                    pts=stat_int("points"),
                    gd=stat_int("pointDifferential", "goaldifference"),
                    gf=stat_int("pointsFor", "goalsfor"),
                )
            )

        if len(rows) >= 3:
            rows = sorted(
                rows,
                key=lambda row: (
                    row.pts if isinstance(row.pts, int) else -999,
                    row.gd if isinstance(row.gd, int) else -999,
                    row.gf if isinstance(row.gf, int) else -999,
                ),
                reverse=True,
            )
            groups[group] = rows[:4]

    return groups


def merge_group_standings(base: Dict[str, Dict[str, TeamRow]], incoming: Dict[str, List[TeamRow]]) -> None:
    for group, rows in incoming.items():
        if group not in base:
            base[group] = {}
        for pos, row in enumerate(rows, start=1):
            base[group][str(pos)] = row


def compute_third_place(groups: Dict[str, Dict[str, TeamRow]]) -> List[Dict[str, Any]]:
    third: List[Dict[str, Any]] = []
    for g in "ABCDEFGHIJKL":
        row = groups.get(g, {}).get("3")
        if not row:
            continue
        third.append({"group": g, "team": row.team, "pts": row.pts, "gd": row.gd, "gf": row.gf, "rank": 0})

    def sort_key(item: Dict[str, Any]) -> Tuple[int, int, int, str]:
        pts = item.get("pts")
        gd = item.get("gd")
        gf = item.get("gf")
        return (
            pts if isinstance(pts, int) else -999,
            gd if isinstance(gd, int) else -999,
            gf if isinstance(gf, int) else -999,
            item.get("group") or "",
        )

    third_sorted = sorted(third, key=sort_key, reverse=True)
    for i, item in enumerate(third_sorted, start=1):
        item["rank"] = i
    return third_sorted


def determine_qualified_third(third_rank: List[Dict[str, Any]]) -> List[str]:
    return [t["group"] for t in third_rank[:8] if t.get("group")]


def load_r32_mapping() -> Dict[str, Dict[str, str]]:
    if not R32_MAPPING_PATH.exists():
        raise RuntimeError("missing r32_third_mapping.json")
    return json.loads(R32_MAPPING_PATH.read_text(encoding="utf-8"))


def build_r32_bracket(groups: Dict[str, Dict[str, TeamRow]], qualified_third_groups: List[str]) -> List[Dict[str, Any]]:
    mapping = load_r32_mapping()
    key = "".join(sorted(qualified_third_groups)) if len(qualified_third_groups) == 8 else ""
    third_assign = mapping.get(key, {}) if key else {}

    def slot_name(group: str, pos: str) -> str:
        row = groups.get(group, {}).get(pos)
        return row.team if row else f"{group}{pos}"

    def third_name(group_letter: str) -> str:
        if not group_letter:
            return "3?"
        row = groups.get(group_letter, {}).get("3")
        return row.team if row else f"{group_letter}3"

    return [
        {"match": 73, "side": "upper", "home": {"slot": "A2", "team": slot_name("A", "2")}, "away": {"slot": "B2", "team": slot_name("B", "2")}},
        {"match": 74, "side": "upper", "home": {"slot": "E1", "team": slot_name("E", "1")}, "away": {"slot": "3?", "team": third_name(third_assign.get("E", "")), "thirdFrom": third_assign.get("E", "")}},
        {"match": 75, "side": "upper", "home": {"slot": "F1", "team": slot_name("F", "1")}, "away": {"slot": "C2", "team": slot_name("C", "2")}},
        {"match": 77, "side": "upper", "home": {"slot": "I1", "team": slot_name("I", "1")}, "away": {"slot": "3?", "team": third_name(third_assign.get("I", "")), "thirdFrom": third_assign.get("I", "")}},
        {"match": 81, "side": "upper", "home": {"slot": "D1", "team": slot_name("D", "1")}, "away": {"slot": "3?", "team": third_name(third_assign.get("D", "")), "thirdFrom": third_assign.get("D", "")}},
        {"match": 82, "side": "upper", "home": {"slot": "G1", "team": slot_name("G", "1")}, "away": {"slot": "3?", "team": third_name(third_assign.get("G", "")), "thirdFrom": third_assign.get("G", "")}},
        {"match": 83, "side": "upper", "home": {"slot": "K2", "team": slot_name("K", "2")}, "away": {"slot": "L2", "team": slot_name("L", "2")}},
        {"match": 84, "side": "upper", "home": {"slot": "H1", "team": slot_name("H", "1")}, "away": {"slot": "J2", "team": slot_name("J", "2")}},
        {"match": 76, "side": "lower", "home": {"slot": "C1", "team": slot_name("C", "1")}, "away": {"slot": "F2", "team": slot_name("F", "2")}},
        {"match": 78, "side": "lower", "home": {"slot": "E2", "team": slot_name("E", "2")}, "away": {"slot": "I2", "team": slot_name("I", "2")}},
        {"match": 79, "side": "lower", "home": {"slot": "A1", "team": slot_name("A", "1")}, "away": {"slot": "3?", "team": third_name(third_assign.get("A", "")), "thirdFrom": third_assign.get("A", "")}},
        {"match": 80, "side": "lower", "home": {"slot": "L1", "team": slot_name("L", "1")}, "away": {"slot": "3?", "team": third_name(third_assign.get("L", "")), "thirdFrom": third_assign.get("L", "")}},
        {"match": 85, "side": "lower", "home": {"slot": "B1", "team": slot_name("B", "1")}, "away": {"slot": "3?", "team": third_name(third_assign.get("B", "")), "thirdFrom": third_assign.get("B", "")}},
        {"match": 86, "side": "lower", "home": {"slot": "J1", "team": slot_name("J", "1")}, "away": {"slot": "H2", "team": slot_name("H", "2")}},
        {"match": 87, "side": "lower", "home": {"slot": "K1", "team": slot_name("K", "1")}, "away": {"slot": "3?", "team": third_name(third_assign.get("K", "")), "thirdFrom": third_assign.get("K", "")}},
        {"match": 88, "side": "lower", "home": {"slot": "D2", "team": slot_name("D", "2")}, "away": {"slot": "G2", "team": slot_name("G", "2")}},
    ]


def fetch_round32_schedule() -> List[Dict[str, Any]]:
    payload = json.loads(fetch_url(ESPN_R32_SCOREBOARD_API, timeout=15))
    events: List[Dict[str, Any]] = []
    for event in payload.get("events", []) or []:
        if (event.get("season") or {}).get("slug") != "round-of-32":
            continue
        comp = (event.get("competitions") or [{}])[0]
        venue = comp.get("venue") or {}
        address = venue.get("address") or {}
        teams: List[str] = []
        for competitor in comp.get("competitors", []) or []:
            team_obj = competitor.get("team") or {}
            name = clean_text(team_obj.get("displayName") or team_obj.get("name") or "")
            if name:
                teams.append(zh_team(name))
        events.append(
            {
                "eventId": event.get("id"),
                "date": event.get("date"),
                "name": event.get("name"),
                "shortName": event.get("shortName"),
                "venue": venue.get("fullName") or "",
                "city": address.get("city") or "",
                "country": address.get("country") or "",
                "teams": teams,
            }
        )
    return events


def slot_from_token(token: str) -> Optional[str]:
    token = (token or "").strip().upper()
    match = re.match(r"([12])([A-L])$", token)
    if not match:
        return None
    return f"{match.group(2)}{match.group(1)}"


def event_candidate_groups(event_name: str) -> List[str]:
    match = re.search(r"Third Place Group\s+([A-L/]+)", event_name or "", flags=re.I)
    if not match:
        return []
    return [g for g in match.group(1).upper().split("/") if g]


def match_schedule_event(match: Dict[str, Any], event: Dict[str, Any]) -> bool:
    match_teams = {match.get("home", {}).get("team"), match.get("away", {}).get("team")}
    match_teams = {t for t in match_teams if t and not re.match(r"^[A-L][123]$", t) and t != "3?"}
    event_teams = {t for t in event.get("teams", []) if t}
    if len(match_teams) == 2 and match_teams == event_teams:
        return True

    short_name = event.get("shortName") or ""
    left, right = (short_name.split(" @ ", 1) + [""])[:2]
    event_slots = {slot_from_token(left), slot_from_token(right)}
    event_slots = {s for s in event_slots if s}
    match_slots = {match.get("home", {}).get("slot"), match.get("away", {}).get("slot")}
    if event_slots and event_slots.issubset(match_slots):
        return True

    known_slot = slot_from_token(right) or slot_from_token(left)
    candidates = set(event_candidate_groups(event.get("name") or ""))
    third_from = match.get("home", {}).get("thirdFrom") or match.get("away", {}).get("thirdFrom")
    if known_slot and known_slot in match_slots and third_from and third_from in candidates:
        return True

    if match_teams.intersection(event_teams):
        candidates = set(event_candidate_groups(event.get("name") or ""))
        if third_from and third_from in candidates:
            return True

    return False


def attach_round32_schedule(r32: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> None:
    used = set()
    for match in r32:
        for event in events:
            event_id = event.get("eventId")
            if event_id in used:
                continue
            if match_schedule_event(match, event):
                match["schedule"] = {
                    "eventId": event_id,
                    "date": event.get("date"),
                    "venue": event.get("venue"),
                    "city": event.get("city"),
                    "country": event.get("country"),
                    "name": event.get("name"),
                    "shortName": event.get("shortName"),
                }
                used.add(event_id)
                break


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    group_map: Dict[str, Dict[str, TeamRow]] = {}
    standings_text = fetch_url(ESPN_STANDINGS_API, timeout=15)
    standings_groups = parse_espn_standings(standings_text)
    if standings_groups:
        merge_group_standings(group_map, standings_groups)

    expected_groups = set("ABCDEFGHIJKL")
    missing_groups = [g for g in sorted(expected_groups) if g not in group_map or len(group_map[g]) < 3]
    if missing_groups:
        raise RuntimeError(f"standings incomplete, missing groups: {','.join(missing_groups)}")

    third_rank = compute_third_place(group_map)
    qualified = determine_qualified_third(third_rank)
    r32 = build_r32_bracket(group_map, qualified)

    schedule_events = fetch_round32_schedule()
    if schedule_events:
        attach_round32_schedule(r32, schedule_events)

    payload = {
        "updatedAt": now_ms(),
        "thirdPlace": third_rank,
        "qualifiedThirdGroups": qualified,
        "r32": r32,
    }

    STATE_SNAPSHOT_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
