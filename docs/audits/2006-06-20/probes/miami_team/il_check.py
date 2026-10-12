"""Injured-list ledger vs Miami results: a player on the list on a game date must not have a box line; dressed count <= 12;
the note's injured-list line names the ledger's players."""
import sys, re, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from collect import *
for s in SEASONS:
    p = CAREER / s / '00_Team/Transactions/injured_list.json'
    if not p.is_file():
        print(s, 'no ledger'); continue
    led = json.loads(p.read_text())['entries']
    hold = json.loads((CAREER / s / '00_Team/Team/Roster/holdings.json').read_text())['entries']
    issues = 0
    for folder, gt in (('06_Regular_Season', 'regular'), ('08_Playoffs', 'playoff')):
        games, _ = closed(s, folder, gt)
        for g in games:
            d = g['result']['game_date']
            on = {e['player'] for e in led if e['placed'] <= d and (e['activated'] is None or e['activated'] > d)}
            box = [r['player_id'] for r in g['result']['player_stats'][g['side']]]
            inact = g['result'].get('inactive', {}).get(g['side'], [])
            clash = on & set(box)
            if clash:
                issues += 1; print(s, d, 'on IL but in box', clash)
            if len(box) + len(inact) > 13:
                issues += 1; print(s, d, 'dressed', len(box), 'inactive', len(inact))
            text = g['note'].read_text()
            m = re.search(r"Miami's injured list for this game: ([^(]*)\(", text)
            if m and d >= '2003-11-12':
                named = {x.strip() for x in m.group(1).strip().rstrip('.').split(',') if x.strip()}
                if named != on:
                    issues += 1; print(s, d, g['note'].name, 'note IL', named, 'ledger', on)
            # box players must be held by Miami on the date
            for pid in box:
                held = [e for e in hold if e['player'] == pid and not e.get('void') and e['from'] <= d and (e['until'] is None or d < e['until'])]
                if not held:
                    issues += 1; print(s, d, pid, 'in Miami box but not held on the date')
    print(s, 'issues', issues)
