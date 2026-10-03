#!/usr/bin/env python3
"""Read-only continuity validation for the player-career repository."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.season_rules import month_week, area_available
from runtime.player_stats import repository_rating_errors

NOTE_STATUSES = {"not_started","active","complete"}
GAME_STATUSES = {"scheduled","played","not_played"}
GAME_RE = re.compile(r"^Game_(\d+)\.md$")
CAP_SEASONS = [f"{year}-{(year+1)%100:02d}" for year in range(2003,2011)]


def require(errors, condition, message):
    if not condition:
        errors.append(message)


def finance_errors(finance, schedules, history):
    """Reconcile the commitment inventory without treating missing costs as zero."""
    errors=[]
    for label, actual in (("finance",finance.get("planning_horizon")),
                          ("contracts",schedules.get("horizon")),
                          ("cap archive",history.get("horizon"))):
        require(errors,actual==CAP_SEASONS,f"{label}: expected eight seasons, 2003-04 through 2010-11")
    projections=schedules.get("projection",[])
    require(errors,[r.get("season") for r in projections]==CAP_SEASONS,"projection must contain every season once, in order")
    option_kinds={"player_option","team_option","early_termination_option"}
    totals={year:{"contract_salary":0,"draft_hold":0,"options":0,"unknown_options":0,"rounded":0} for year in CAP_SEASONS}
    for player in schedules.get("players",[]):
        amounts=player.get("schedule",{})
        kinds=player.get("amount_kind",{})
        require(errors,set(amounts)==set(kinds),f"{player.get('player')}: every scheduled amount needs an accounting kind")
        for year,amount in amounts.items():
            kind=kinds.get(year)
            require(errors,year in totals,f"{player.get('player')}: scheduled year outside horizon")
            require(errors,kind in option_kinds|{"contract_salary","draft_hold","unsigned_rights"},f"{player.get('player')}: unsupported accounting kind")
            require(errors,amount is None or type(amount) is int and amount>=0,f"{player.get('player')}: salary must be whole nonnegative dollars or null")
            if year not in totals:
                continue
            precision=player.get("amount_precision",{}).get(year,"whole_dollars")
            require(errors,precision in {"whole_dollars","reported_rounded"},f"{player.get('player')}: unsupported source precision")
            if precision=="reported_rounded":
                require(errors,kind=="contract_salary" and type(amount) is int,f"{player.get('player')}: rounded report needs a priced contract salary")
                totals[year]["rounded"]+=1
            if kind in option_kinds and amount is None:
                totals[year]["unknown_options"]+=1
            elif type(amount) is int and kind in option_kinds:
                totals[year]["options"]+=amount
            elif type(amount) is int and kind in {"contract_salary","draft_hold"}:
                totals[year][kind]+=amount
            elif kind=="unsigned_rights":
                require(errors,amount is None,f"{player.get('player')}: unsigned rights cannot silently book a salary")
    for row in projections:
        year=row.get("season")
        if year not in totals:
            continue
        t=totals[year]
        base=t["contract_salary"]+t["draft_hold"]
        expected={"scheduled_contract_salary":t["contract_salary"],"unsigned_first_round_holds":t["draft_hold"],
                  "known_conditional_salary":t["options"],"unpriced_option_count":t["unknown_options"],
                  "known_base_allocations":base,"base_plus_priced_options":base+t["options"],
                  "reported_rounded_salary_count":t["rounded"],
                  "subtotal_precision":"includes_rounded_report" if t["rounded"] else "whole_dollars"}
        for key,value in expected.items():
            require(errors,row.get(key)==value,f"{year}: {key} does not reconcile to contract inventory")
        for key,value in (("known_baseline",base),("conditional_known_amounts",t["options"]),("conditional_unknown_count",t["unknown_options"])):
            require(errors,schedules.get(key,{}).get(year)==value,f"{year}: {key} does not reconcile")
        # This is an existing-obligation projection. Future roster costs remain unassessed.
        for key in ("free_agent_holds","other_cap_charges","total_team_salary","cap_space"):
            require(errors,key in row and row[key] is None,f"{year}: unresolved {key} must remain null")
    current=totals[CAP_SEASONS[0]]
    expected_current={"scheduled_contract_salary_subtotal":current["contract_salary"],
                      "known_counted_salary_before_free_agent_holds":current["contract_salary"]+current["draft_hold"],
                      "known_pending_option_salary":current["options"],
                      "known_base_plus_priced_options":current["contract_salary"]+current["draft_hold"]+current["options"],
                      "reported_rounded_salary_count":current["rounded"],
                      "subtotal_precision":"includes_rounded_report" if current["rounded"] else "whole_dollars"}
    for key,value in expected_current.items():
        require(errors,finance.get(key)==value,f"finance: {key} does not reconcile to contracts")
    components=finance.get("known_current_components",[])
    require(errors,sum(c.get("amount",0) for c in components)==expected_current["known_counted_salary_before_free_agent_holds"],"finance: current component subtotal mismatch")
    holds=finance.get("free_agent_holds",[])
    require(errors,Counter(h.get("player") for h in holds)==Counter(schedules.get("expiring_or_unresolved_without_scheduled_2003_04_salary",[])),"finance: free-agent hold review is incomplete or duplicated")
    scheduled_names={p.get("player") for p in schedules.get("players",[])}
    require(errors,not scheduled_names.intersection(h.get("player") for h in holds),"finance: contract or pending option also counted as a free-agent hold")
    for hold in holds:
        amount=hold.get("amount")
        require(errors,amount is None or type(amount) is int and amount>=0,"finance: hold must be whole nonnegative dollars or null")
        status=hold.get("calculation_status")
        if status in {"prior_salary_disputed","maximum_salary_limit_pending"}:
            require(errors,amount is None,f"{hold.get('player')}: unresolved hold cannot be booked")
        elif status=="minimum_salary_override":
            require(errors,amount==hold.get("applicable_minimum_cap_amount"),f"{hold.get('player')}: minimum hold does not reconcile")
        elif status=="derived_from_prior_salary":
            multiplier={"early_bird":130,"non_bird":120}.get(hold.get("rights_type"))
            prior=hold.get("prior_season_salary")
            require(errors,multiplier is not None and type(prior) is int and amount==prior*multiplier//100,
                    f"{hold.get('player')}: hold must use the 1999 CBA multiplier")
        else:
            require(errors,False,f"{hold.get('player')}: unsupported hold calculation status")
        require(errors,hold.get("effective_no_earlier_than")=="2003-07-01","finance: expiring-contract holds must remain upcoming-year projections")
        require(errors,hold.get("renouncement_status")=="not_recorded","June 26: no later renouncement may be assumed")
    priced_holds=sum(h["amount"] for h in holds if type(h.get("amount")) is int)
    unknown_holds=sum(h.get("amount") is None for h in holds)
    require(errors,finance.get("known_free_agent_holds_subtotal")==priced_holds,"finance: partial free-agent hold subtotal does not reconcile")
    require(errors,finance.get("unpriced_free_agent_hold_count")==unknown_holds,"finance: unpriced free-agent hold count does not reconcile")
    require(errors,"free_agent_hold_total" in finance and finance["free_agent_hold_total"] is None,"finance: incomplete free-agent hold total must remain null")
    for row in projections:
        current_year=row.get("season")==CAP_SEASONS[0]
        require(errors,row.get("known_free_agent_holds")== (priced_holds if current_year else None),f"{row.get('season')}: partial hold projection mismatch")
        require(errors,row.get("unpriced_free_agent_hold_count")== (unknown_holds if current_year else None),f"{row.get('season')}: unpriced hold projection mismatch")
    option_rows={p["player"]:(p["amount_kind"][CAP_SEASONS[0]],p["schedule"][CAP_SEASONS[0]])
                 for p in schedules.get("players",[]) if p.get("amount_kind",{}).get(CAP_SEASONS[0]) in option_kinds}
    pending=finance.get("pending_control_items",[])
    require(errors,Counter(p.get("player") for p in pending)==Counter(option_rows.keys()),"finance: pending option register does not match contracts")
    for item in pending:
        require(errors,(item.get("type"),item.get("amount"))==option_rows.get(item.get("player")),"finance: pending option amount/type mismatch")
        require(errors,item.get("status")=="pending" and item.get("deadline")=="2003-06-30","June 26: option decision must remain pending")
    for p in schedules.get("players",[]):
        if p.get("status")=="unsigned_second_round_draft_rights":
            require(errors,p.get("current_cap_hold")==0,"1999 CBA: unsigned second-round rights have no individual draft hold")
    require(errors,finance.get("era_rules",{}).get("early_bird_hold_multiplier")==1.3,"1999 CBA: Early Bird hold multiplier must be 130%")
    for key in ("live_official_salary_cap","live_official_tax_threshold","cap_space","cap_room","tax_payroll","luxury_tax_bill"):
        require(errors,key in finance and finance[key] is None,f"June 26: {key} must remain unresolved")
    expected_caps=dict(zip(CAP_SEASONS,(43840000,43870000,49500000,53135000,55630000,58680000,57700000,58044000)))
    archive=history.get("seasons",[])
    require(errors,[r.get("season") for r in archive]==CAP_SEASONS,"cap archive must contain each season once, in order")
    require(errors,{r.get("season"):r.get("salary_cap") for r in archive}==expected_caps,"eight-season historical cap reference changed")
    for row in archive:
        publication=row.get("published_date")
        effective=row.get("effective_date")
        live=bool(publication and publication<=finance["as_of"] and (not effective or effective<=finance["as_of"]))
        require(errors,row.get("live_at_checkpoint")==live,f"{row.get('season')}: publication/activation gate mismatch")
    return errors


def markdown_tables(text):
    """Yield headers and data rows from the reports' simple pipe tables."""
    for block in re.findall(r"(?:^\|[^\n]*\|\n)+",text,re.M):
        rows=[[cell.strip() for cell in line.strip().strip('|').split('|')] for line in block.splitlines()]
        if len(rows)>=2 and all(re.fullmatch(r":?-+:?",cell) for cell in rows[1]):
            yield rows[0],rows[2:]


LINK_TEXT=re.compile(r"^\[([^\]]+)\]\(([^)]+)\)$")


def cell_text(cell):
    """A table cell's visible text; a Markdown link reads as its label."""
    match=LINK_TEXT.match(cell.strip())
    return match.group(1) if match else cell.strip()


def report_errors(root, player, team):
    """Check navigation and player coverage across every existing period."""
    errors=[]
    stats=player/"Stats_and_Awards"
    pages=[root/"README.md",*(team/"Finances").glob("*.md"),*stats.rglob("*.md")]
    registry=json.loads((stats/"League/player_registry.json").read_text(encoding="utf-8"))["players"]
    roster=json.loads((team/"Team/Roster/roster.json").read_text(encoding="utf-8"))["players"]
    expected_league=Counter(p["name"] for p in registry)
    expected_team=Counter(p["name"] for p in roster)
    for page in pages:
        text=page.read_text(encoding="utf-8")
        label=str(page.relative_to(root))
        require(errors,text.count("<details>")==text.count("</details>"),f"{label}: unbalanced detail sections")
        for href in re.findall(r"\[[^\]\n]+\]\(([^)\s]+)\)",text):
            target=urlsplit(href)
            if not target.scheme and target.path:
                require(errors,(page.parent/unquote(target.path)).exists(),f"{label}: broken link {href}")
        tables=list(markdown_tables(text))
        for header,rows in tables:
            require(errors,all(len(row)==len(header) for row in rows),f"{label}: table column mismatch")
        if page.name in {"League_Stats.md","Team_Stats.md"}:
            production=[row for header,rows in tables if header[:1]==["Player"] and ("PPG" in header or "PTS" in header) for row in rows]
            actual=Counter(cell_text(row[0]) for row in production)
            require(errors,all(count==1 for count in actual.values()),f"{label}: duplicate player production rows")
            # Completed Miami periods retain former players; today's roster is not their source.
            if page.name=="League_Stats.md":
                require(errors,actual==expected_league,f"{label}: player production rows missing or duplicated")
            elif "As of June 26, 2003: not started." in text:
                require(errors,actual==expected_team,f"{label}: initial Miami control-register coverage mismatch")
        if page.name=="League_Stats.md":
            for pos in {p["position"] for p in registry}:
                group=re.search(rf"<summary>{pos} ·.*?</summary>(.*?)</details>",text,re.S)
                require(errors,group is not None,f"{label}: missing {pos} position group")
                if group:
                    names=Counter(cell_text(row[0]) for header,rows in markdown_tables(group[1]) if "PPG" in header or "PTS" in header for row in rows)
                    for header,rows in markdown_tables(group[1]):
                        for row in rows:
                            require(errors,LINK_TEXT.match(row[0].strip()) is not None,f"{label}: {cell_text(row[0])} is not linked to a league card")
                    require(errors,names==Counter(p["name"] for p in registry if p["position"]==pos),f"{label}: {pos} membership mismatch")
                    columns={column for header,_ in markdown_tables(group[1]) for column in header}
                    require(errors,{"Age","Pos","GS","MP","FG","FGA","3P","3PA","2P","2PA","eFG%","FT","FTA","ORB","DRB","TRB","PF","PTS"}<=columns,f"{label}: incomplete league per-game columns")
        if page.name=="League_Awards.md" and page.parent.name!="2003-04":
            shortlists=[rows for header,rows in tables if header[:2]==["Conference","Rank slot"]]
            expected_count=1 if page.parent.name.startswith("Week_") else 2
            require(errors,len(shortlists)==expected_count,f"{label}: conference award shortlists missing")
            for rows in shortlists:
                require(errors,Counter((r[0],r[1]) for r in rows)==Counter((conference,str(rank)) for conference in ("East","West") for rank in (1,2,3)),f"{label}: each conference needs three shortlist slots")
            require(errors,not any("First-place votes" in header or "Points" in header for header,_ in tables),f"{label}: weekly/monthly shortlists must not invent vote totals")
    return errors


def front_matter(path):
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("empty file")
    if not text.startswith("---\n"):
        raise ValueError("missing front matter")
    parts = text.split("---\n",2)
    if len(parts) < 3:
        raise ValueError("unterminated front matter")
    data = {}
    for line in parts[1].splitlines():
        if ":" in line:
            k,v = line.split(":",1)
            data[k.strip()] = v.strip()
    return data


def discover():
    career = ROOT / "career"
    players = [p for p in career.iterdir() if p.is_dir()]
    if len(players) != 1:
        raise ValueError("career must contain exactly one player directory")
    years = [p for p in players[0].iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}", p.name)]
    if len(years) != 1:
        raise ValueError("player directory must contain exactly one active season directory")
    return players[0], years[0]


def validate_game(path, errors, play_in_game_1=False):
    try:
        data = front_matter(path)
    except ValueError as exc:
        errors.append(f"{path.relative_to(ROOT)}: {exc}")
        return None
    require(errors, data.get("type") == "game", f"{path.relative_to(ROOT)}: wrong type")
    status = data.get("status")
    require(errors, status in GAME_STATUSES, f"{path.relative_to(ROOT)}: invalid status")
    if status == "scheduled":
        require(errors, bool(data.get("date")), f"{path.relative_to(ROOT)}: scheduled game needs date")
        require(errors, bool(data.get("opponent")), f"{path.relative_to(ROOT)}: scheduled game needs opponent")
        require(errors, not data.get("result"), f"{path.relative_to(ROOT)}: scheduled game cannot have result")
    elif status == "played":
        require(errors, bool(data.get("date")), f"{path.relative_to(ROOT)}: played game needs date")
        require(errors, bool(data.get("opponent")), f"{path.relative_to(ROOT)}: played game needs opponent")
        require(errors, bool(data.get("result")), f"{path.relative_to(ROOT)}: played game needs result")
    elif status == "not_played":
        require(errors, bool(data.get("reason")), f"{path.relative_to(ROOT)}: not_played game needs reason")
        require(errors, not data.get("result"), f"{path.relative_to(ROOT)}: not_played game cannot have result")
    if play_in_game_1:
        require(errors, data.get("next_game_required") in {"true","false"}, f"{path.relative_to(ROOT)}: next_game_required must be true/false")
    return data


def validate_sequence(folder, errors, maximum=None):
    nums = sorted(int(m.group(1)) for path in folder.glob("Game_*.md") if (m := GAME_RE.match(path.name)))
    if maximum is not None:
        require(errors, all(n <= maximum for n in nums), f"{folder.relative_to(ROOT)}: game number exceeds {maximum}")
    if nums:
        require(errors, nums == list(range(1,max(nums)+1)), f"{folder.relative_to(ROOT)}: game files must be sequential without gaps")


RIGHTS_RULE_KEYS = ("previous_salary", "joined_miami", "seasons_with_miami_for_bird", "nba_seasons_before_2003_04", "bird_status",
                    "cap_hold", "cap_hold_percent", "above_league_average_salary", "qualifying_offer")


def rights_errors(root):
    """Miami's free-agent rights file against the rule builder and the league rights file.

    At the June 26 checkpoint the file must equal the builder's output. Once the clock has moved, the
    drivers add state the builder does not know (qualifying offers tendered, re-signings, departures,
    a declined player option's new row), so every builder player must still agree on the rule-computed
    keys while extra keys and extra rows are allowed."""
    from scripts.build_miami_free_agent_rights import OUT as RIGHTS_PATH, build as build_rights
    errors = []
    root = Path(root)
    try:
        state = json.loads((root / "career/Dwyane_Wade/2003-04/current_state.json").read_text(encoding="utf-8"))
        current = json.loads((root / RIGHTS_PATH).read_text(encoding="utf-8"))
        built = json.loads(json.dumps(build_rights(root)))
        if state.get("current_date", "2003-06-26") <= "2003-06-26":
            if current != built:
                errors.append("Miami free-agent rights are stale; run scripts/build_miami_free_agent_rights.py")
        else:
            rows = {p["player"]: p for p in current["players"]}
            for p in built["players"]:
                row = rows.get(p["player"])
                if row is None:
                    errors.append(f"Miami free-agent rights: {p['player']} is missing from the file")
                    continue
                for key in RIGHTS_RULE_KEYS:
                    if row.get(key) != p.get(key):
                        errors.append(f"Miami free-agent rights: {p['player']}: {key} disagrees with the rule builder")
        league_rights = json.loads((root / "library/2003/league/nba_2003_free_agent_rights.json").read_text(encoding="utf-8"))
        if any(p["status"] in ("free_agent_restricted", "free_agent_unrestricted")
               for c in league_rights["clubs"].values() for p in c["free_agents"]):
            errors.append("league free-agent rights must not carry restricted/unrestricted marks (qualifying offers are June 30 decisions)")
        bird_names = {"bird": "larry_bird", "early_bird": "early_bird", "non_bird": "non_bird"}
        league_miami = {p["bbr_id"]: p for p in league_rights["clubs"]["Miami Heat"]["free_agents"]}
        for p in current["players"]:
            other = league_miami.get(p["bbr_id"])
            if other is None:
                continue                      # a row the drivers added (a declined player option) is not in the league file
            if (bird_names.get(other.get("bird_class")), other.get("cap_hold_amount"), other.get("qualifying_offer_amount")) != \
                    (p["bird_status"], p["cap_hold"], p["qualifying_offer"]):
                errors.append(f"Miami free-agent rights disagree with the league rights file for {p['player']}")
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f"cannot validate Miami free-agent rights: {exc}")
    return errors


def validate():
    errors=repository_rating_errors(ROOT)
    try:
        config=json.loads((ROOT/"foundation/season_structure.json").read_text(encoding="utf-8"))
        player,season=discover()
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        return [f"cannot load required structure: {exc}"]

    require(errors, player.name == "Dwyane_Wade", "active player directory must be Dwyane_Wade")
    require(errors, season.name == "2003-04", "active season directory must be 2003-04")
    require(errors, (player/"Dwyane_Wade_Player_Profile.md").is_file(), "missing Dwyane Wade player profile")

    league_dir=ROOT/"library/2003/league"
    draft_library=league_dir/"nba_2003_draft_class.json"
    end_library=league_dir/"nba_2003_end_of_season.json"
    require(errors,draft_library.is_file(),"missing 2003 draft-class league source")
    require(errors,end_library.is_file(),"missing 2003 end-of-season league source")
    require(errors,not (season/"nba_2003_draft_class.json").exists(),"league draft source must not live in season root")
    require(errors,not (season/"nba_2003_end_of_season.json").exists(),"league roster source must not live in season root")
    for source_path, expected_as_of, expected_clubs, expected_players in (
        (draft_library,"2003 NBA draft (June 26, 2003), after draft-night trades",27,58),
        (end_library,"end of 2002-03 season (each club's final game)",29,350),
    ):
        if source_path.is_file():
            try:
                source=json.loads(source_path.read_text(encoding="utf-8"))
                require(errors,source.get("league")=="NBA",f"{source_path.relative_to(ROOT)}: league must be NBA")
                require(errors,source.get("season")==2003,f"{source_path.relative_to(ROOT)}: season must be 2003")
                require(errors,source.get("as_of")==expected_as_of,f"{source_path.relative_to(ROOT)}: as_of mismatch")
                clubs=source.get("clubs")
                require(errors,isinstance(clubs,dict) and len(clubs)==expected_clubs,f"{source_path.relative_to(ROOT)}: club count mismatch")
                if isinstance(clubs,dict):
                    player_count=sum(len(club.get("players",[])) for club in clubs.values() if isinstance(club,dict))
                    require(errors,player_count==expected_players,f"{source_path.relative_to(ROOT)}: player count mismatch")
            except json.JSONDecodeError as exc:
                errors.append(f"{source_path.relative_to(ROOT)}: invalid JSON: {exc}")

    state_path=season/"current_state.json"
    require(errors,state_path.is_file(),"missing season current state")
    if state_path.is_file():
        try:
            state=json.loads(state_path.read_text(encoding="utf-8"))
            require(errors,state.get("initialized") is True,"career must be initialized")
            require(errors,state.get("season")=="2003-04","current state season mismatch")
            require(errors,isinstance(state.get("current_date"),str) and state["current_date"]>="2003-06-26","career clock before the June 26 checkpoint")
            require(errors,state.get("team")=="Miami Heat","current team mismatch")
        except json.JSONDecodeError as exc:
            errors.append(f"current_state.json invalid: {exc}")

    team=season/"00_Team"
    required_team_files=(
        "team_config.json",
        "Organization/organization.json",
        "Organization/Micky_Arison.md",
        "Organization/Pat_Riley.md",
        "Organization/Randy_Pfund.md",
        "Organization/Andy_Elisburg.md",
        "Organization/Chet_Kammerer.md",
        "Team/Roster/roster.json",
        "Team/Depth_Chart/depth_chart.json",
        "Team/Depth_Chart/depth_chart.md",
        "Team/Player_Cards/TEMPLATE.md",
        "Finances/finance.json",
        "Finances/cap_sheet.md",
        "Finances/contract_schedules.json",
        "Finances/league_cap_history.json",
    )
    for rel in required_team_files:
        require(errors,(team/rel).is_file(),f"missing AI/GM team file: 00_Team/{rel}")

    for rel in ("team_config.json","Organization/organization.json","Team/Roster/roster.json","Team/Depth_Chart/depth_chart.json","Finances/finance.json"):
        path=team/rel
        if path.is_file():
            try:
                data=json.loads(path.read_text(encoding="utf-8"))
                require(errors,data.get("owner")=="ai_gm",f"{path.relative_to(ROOT)} must be AI/GM-owned")
            except json.JSONDecodeError as exc:
                errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")

    roster_path=team/"Team/Roster/roster.json"
    if roster_path.is_file():
        roster=json.loads(roster_path.read_text(encoding="utf-8"))
        players=roster.get("players",[])
        ids=[p.get("id") for p in players]
        require(errors,len(ids)==len(set(ids)),"roster player ids must be unique")
        require(errors,{"dwyane_wade","jerome_beasley"} <= set(ids),"draft picks missing from roster/control register")
        required_card_sections=[
            "## Scouting report",
            "## Player grades",
            "## Changes and coaching notes",
            "## Sources and uncertainty",
            "## Regular-season statistics by year",
            "## Playoff statistics by year",
            "## Awards and honors",
        ]
        for p in players:
            card=team/"Team/Player_Cards"/f"{p.get('id')}.md"
            require(errors,card.is_file(),f"missing player card for {p.get('name')}")
            if card.is_file():
                text=card.read_text(encoding="utf-8")
                positions=[text.find(section) for section in required_card_sections]
                require(errors,all(pos >= 0 for pos in positions),f"{card.relative_to(ROOT)}: missing canonical template section")
                if all(pos >= 0 for pos in positions):
                    require(errors,positions==sorted(positions),f"{card.relative_to(ROOT)}: template section order changed")
                    require(errors,re.findall(r"^## .+$",text,re.M)[-3:]==required_card_sections[-3:],f"{card.relative_to(ROOT)}: regular-season stats, playoffs and awards must remain the final sections")

    try:
        at_checkpoint=json.loads(state_path.read_text(encoding="utf-8")).get("current_date")=="2003-06-26"
    except (OSError, ValueError):
        at_checkpoint=True
    finance_path=team/"Finances/finance.json"
    if finance_path.is_file() and at_checkpoint:
        finance=json.loads(finance_path.read_text(encoding="utf-8"))
        require(errors,finance.get("as_of")=="2003-06-26","finance snapshot date mismatch")
        require(errors,finance.get("cap_room") is None,"June 26 cap room must remain unresolved")
        pending={x.get("player"):x for x in finance.get("pending_control_items",[])}
        require(errors,pending.get("Anthony Carter",{}).get("status")=="pending","Anthony Carter option must still be pending on June 26")
        require(errors,finance.get("live_official_salary_cap") is None,"June 26 live official cap must remain unpublished")
        require(errors,finance.get("historical_actual_salary_cap")==43840000,"2003-04 historical actual cap must be $43.84M")
        require(errors,finance.get("known_counted_salary_before_free_agent_holds")==32066078,"June 26 reported baseline must include Ellis's existing contract")

    history_path=team/"Finances/league_cap_history.json"

    cap_sheet_path=team/"Finances/cap_sheet.md"
    if cap_sheet_path.is_file():
        cap_sheet=cap_sheet_path.read_text(encoding="utf-8")
        for heading in ("## Current cap position","## Eight-season commitments","## Payroll notes","## Cap reconciliation"):
            require(errors,heading in cap_sheet,f"Finances/cap_sheet.md missing {heading}")
        require(errors,all(year in cap_sheet for year in CAP_SEASONS),"cap sheet must show the eight-season window")

    schedules_path=team/"Finances/contract_schedules.json"
    if schedules_path.is_file():
        schedules=json.loads(schedules_path.read_text(encoding="utf-8"))
        require(errors,schedules.get("known_baseline",{}).get("2003-04")==32066078,"contract schedule baseline mismatch")
        wade=next((x for x in schedules.get("players",[]) if x.get("player")=="Dwyane Wade"),{})
        if wade.get("status")=="unsigned_first_round_draft_rights":
            require(errors,wade.get("current_cap_hold")==2197000,"Wade unsigned rookie-scale cap hold must be $2.197M")
        if history_path.is_file() and finance_path.is_file() and at_checkpoint:
            history=json.loads(history_path.read_text(encoding="utf-8"))
            errors.extend(finance_errors(finance,schedules,history))

    require(errors, config.get("week_definition") == {"1":"1-7","2":"8-14","3":"15-21","4":"22-end"}, "week definition changed")
    require(errors, month_week(1)==1 and month_week(7)==1, "Week 1 rule failed")
    require(errors, month_week(8)==2 and month_week(14)==2, "Week 2 rule failed")
    require(errors, month_week(15)==3 and month_week(21)==3, "Week 3 rule failed")
    require(errors, month_week(22)==4 and month_week(31)==4, "Week 4 rule failed")

    stats_root=player/"Stats_and_Awards"
    stats_year=stats_root/season.name
    require(errors,(stats_root/"README.md").is_file(),"missing Stats_and_Awards index")
    require(errors,(stats_year/"README.md").is_file(),"missing yearly stats and awards page")
    for month,spec in config["regular_season"].items():
        month_dir=stats_year/spec["folder"]
        require(errors,(month_dir/"README.md").is_file(),f"missing monthly stats page: {month}")
        for week in spec["weeks"]:
            require(errors,(month_dir/f"Week_{week}"/"README.md").is_file(),f"missing weekly stats page: {month} Week {week}")

    league_stats_root=player/"Stats_and_Awards"/"League"
    league_registry=league_stats_root/"player_registry.json"
    require(errors,league_registry.is_file(),"missing league player registry")
    if league_registry.is_file():
        registry=json.loads(league_registry.read_text(encoding="utf-8"))
        require(errors,registry.get("player_count")==407,"league player registry count changed")
        positions=[p.get("position") for p in registry.get("players",[])]
        require(errors,all(pos in {"PG","SG","SF","F","PF","C"} for pos in positions),"league registry has unsupported position")
    league_year=league_stats_root/season.name
    require(errors,(league_year/"League_Stats.md").is_file(),"missing yearly league stats page")
    require(errors,(league_year/"League_Awards.md").is_file(),"missing yearly league awards page")
    for month,spec in config["regular_season"].items():
        league_month=league_year/spec["folder"]
        require(errors,(league_month/"League_Stats.md").is_file(),f"missing monthly league stats page: {month}")
        require(errors,(league_month/"League_Awards.md").is_file(),f"missing monthly league awards page: {month}")
        for week in spec["weeks"]:
            league_week=league_month/f"Week_{week}"
            require(errors,(league_week/"League_Stats.md").is_file(),f"missing weekly league stats page: {month} Week {week}")
            require(errors,(league_week/"League_Awards.md").is_file(),f"missing weekly league awards page: {month} Week {week}")

    team_stats_root=player/"Stats_and_Awards"/"Team"
    team_stats_year=team_stats_root/season.name
    require(errors,(team_stats_root/"README.md").is_file(),"missing Team stats index")
    require(errors,(team_stats_year/"Team_Stats.md").is_file(),"missing yearly team stats page")
    for month,spec in config["regular_season"].items():
        team_month=team_stats_year/spec["folder"]
        require(errors,(team_month/"Team_Stats.md").is_file(),f"missing monthly team stats page: {month}")
        for week in spec["weeks"]:
            team_week=team_month/f"Week_{week}"
            require(errors,(team_week/"Team_Stats.md").is_file(),f"missing weekly team stats page: {month} Week {week}")

    for area in config["areas"]:
        folder=season/area["folder"]
        if not area_available(area, season.name):
            require(errors,not any(folder.rglob("Game_*.md")),f"{area['folder']} cannot own games in {season.name}")
            continue
        require(errors,folder.is_dir(),f"missing season area: {area['folder']}")
        if area["order"] in {1,2,3,4,5,9}:
            note=folder/"note.md"
            require(errors,note.is_file(),f"missing phase note: {note.relative_to(ROOT)}")
            if note.is_file():
                try:
                    data=front_matter(note)
                    require(errors,data.get("type")=="phase",f"{note.relative_to(ROOT)}: wrong type")
                    require(errors,data.get("status") in NOTE_STATUSES,f"{note.relative_to(ROOT)}: bad status")
                except ValueError as exc:
                    errors.append(f"{note.relative_to(ROOT)}: {exc}")

    regular=season/"06_Regular_Season"
    day_ranges={1:"1-7",2:"8-14",3:"15-21",4:"22-end"}
    for month,spec in config["regular_season"].items():
        mdir=regular/spec["folder"]
        for week in spec["weeks"]:
            wdir=mdir/f"Week_{week}"
            note=wdir/"note.md"
            require(errors,note.is_file(),f"missing week note: {note.relative_to(ROOT)}")
            if note.is_file():
                try:
                    data=front_matter(note)
                    require(errors,data.get("type")=="regular_season_week",f"{note.relative_to(ROOT)}: wrong type")
                    require(errors,data.get("status") in NOTE_STATUSES,f"{note.relative_to(ROOT)}: bad status")
                    require(errors,data.get("month")==month,f"{note.relative_to(ROOT)}: month mismatch")
                    require(errors,data.get("week")==str(week),f"{note.relative_to(ROOT)}: week mismatch")
                    require(errors,data.get("days")==day_ranges[week],f"{note.relative_to(ROOT)}: days mismatch")
                except ValueError as exc:
                    errors.append(f"{note.relative_to(ROOT)}: {exc}")
            validate_sequence(wdir,errors)
            for game in wdir.glob("Game_*.md"):
                validate_game(game,errors)

    playin=season/"07_Play_In_Tournament"
    validate_sequence(playin,errors,2)
    g1=playin/"Game_1.md"
    g2=playin/"Game_2.md"
    g1meta=validate_game(g1,errors,True) if g1.exists() else None
    if g2.exists():
        validate_game(g2,errors)
        require(errors,g1meta is not None,"Play-In Game 2 exists without Game 1")
        if g1meta is not None:
            require(errors,g1meta.get("status")=="played","Play-In Game 2 requires played Game 1")
            require(errors,g1meta.get("next_game_required")=="true","Play-In Game 2 requires next_game_required: true")

    playoffs=season/"08_Playoffs"
    for rnd in config["playoffs"]["rounds"]:
        rdir=playoffs/rnd["folder"]
        validate_sequence(rdir,errors,7)
        for game in rdir.glob("Game_*.md"):
            validate_game(game,errors)

    errors.extend(rights_errors(ROOT))

    from runtime.decisions import decision_errors, find_decisions
    for path in find_decisions(ROOT):
        try:
            errors.extend(f"{path.relative_to(ROOT)}: {e}" for e in decision_errors(json.loads(path.read_text(encoding="utf-8"))))
        except ValueError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    from runtime.rookie_contract import log_errors
    for path in (ROOT / "career").rglob("negotiation_log.json"):
        errors.extend(f"{path.relative_to(ROOT)}: {e}" for e in log_errors(json.loads(path.read_text(encoding="utf-8")), ROOT))

    from runtime.rosters import roster_errors
    errors.extend(roster_errors(ROOT))
    from runtime.negotiation import negotiation_errors
    errors.extend(negotiation_errors(ROOT))
    from runtime.signing import ledger_errors
    errors.extend(ledger_errors(ROOT))
    from runtime.rotations import holdings_errors
    errors.extend(holdings_errors(ROOT))
    from runtime.signing import trade_record_errors
    errors.extend(trade_record_errors(ROOT))
    from runtime.standing import season_close_errors, standing_errors
    errors.extend(standing_errors(ROOT))
    errors.extend(season_close_errors(ROOT))
    from runtime.consultations import consultation_errors
    errors.extend(consultation_errors(ROOT))

    from runtime.contracts import contract_errors
    errors.extend(contract_errors(ROOT))

    from runtime.trajectories import trajectory_errors
    errors.extend(trajectory_errors(ROOT))

    from runtime.prospects import rookie_errors
    errors.extend(rookie_errors(ROOT))

    from runtime.schedule import schedule_errors
    errors.extend(schedule_errors(ROOT))

    from runtime.game_requests import find_requests, request_errors
    errors.extend(request_errors(ROOT))
    from runtime.season_games import is_league_slate
    for request in find_requests(ROOT):
        if is_league_slate(request):
            continue                      # the league slate has no game notes: its results are league records
        note=request.with_name(request.name.replace(".request.json",".md"))
        require(errors,note.is_file(),f"{request.relative_to(ROOT)}: no matching game note {note.name}")

    errors.extend(report_errors(ROOT,player,team))
    from runtime.league_cards import card_errors
    errors.extend(card_errors(ROOT))
    from runtime.player_reports import report_errors as player_report_errors
    errors.extend(player_report_errors(ROOT,player))
    return errors


def main():
    errors=validate()
    if errors:
        print("Repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
