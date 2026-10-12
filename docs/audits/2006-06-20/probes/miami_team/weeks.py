"""Every closed Miami regular-season game sits in the week folder of its date, and is covered by exactly one Team week page."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from collect import *
TEAM = CAREER / 'Stats_and_Awards/Team'
for s in SEASONS:
    games, _ = closed(s)
    pages = [p for p in (TEAM / s).rglob('Week_*/Team_Stats.md')]
    scopes = [scope_of_page(p.relative_to(TEAM / s), s) for p in pages]
    bad = 0; cover = 0
    for g in games:
        d = g['result']['game_date']
        rel = g['note'].relative_to(CAREER / s / '06_Regular_Season')
        st, en = scope_of_page(rel, s)
        if not (st <= d <= en):
            bad += 1; print('misfiled', rel, d)
        n = sum(1 for a, b in scopes if a <= d <= b)
        if n != 1:
            print('coverage', d, n)
        cover += n
    # numbering inside week folders
    print(s, len(games), 'misfiled', bad, 'covered', cover, 'week pages', len(pages))
    # duplicates of event ids
    ids = [g['result']['event_id'] for g in games]
    print('  unique events', len(set(ids)) == len(ids), ' home', sum(g['side']=='home' for g in games), 'away', sum(g['side']=='away' for g in games))
