import sys, json, re, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
L = ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League'
cards = pickle.load(open('cards.pkl','rb'))
def page_rows(path):
    out = {}
    for line in path.read_text(encoding='utf-8').split('\n'):
        m = re.match(r'^\| \[([^\]]+)\]\((?:\.\./)+Players/([^)]+)\.md\) \|(.*)$', line)
        if m:
            cells = [c.strip() for c in m.group(3).strip().strip('|').split('|')]
            out.setdefault(m.group(2), []).append((m.group(1), cells))
    return out
season = page_rows(L / '2005-06/League_Stats.md')
print('page players', len(season), 'dupes', [k for k, v in season.items() if len(v) > 1][:5])
missing_on_page = [rid for rid in cards if rid not in season]
print('cards not on season page', len(missing_on_page), missing_on_page[:10])
stat_diff, age_diff, club_diff = [], [], []
for rid, c in cards.items():
    if rid not in season: continue
    name, cells = season[rid][0]
    # card season table: first table under '### Season'
    t = next(t for t in c['tables'] if t[0] == '### Season')
    row = t[2][0]
    # row: Scope, Age, Team, Lg, Pos, G ... TS%, Awards
    card_stats = row[5:-1]
    page_stats = cells[4:]
    if card_stats != page_stats:
        stat_diff.append((rid, card_stats[:6], page_stats[:6]))
    if row[1] != cells[0]: age_diff.append((rid, row[1], cells[0]))
    if row[2] != cells[1]: club_diff.append((rid, name, row[2], cells[1]))
print('stat diffs', len(stat_diff), stat_diff[:5])
print('age diffs', len(age_diff), age_diff[:10])
print('club diffs', len(club_diff))
for x in club_diff[:40]: print('  ', x)
pickle.dump(club_diff, open('season_club_diff.pkl','wb'))
