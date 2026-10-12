import sys, json, re, pickle, collections
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
L = ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League'
cards = pickle.load(open('cards.pkl','rb'))
def page_rows(path):
    out = {}
    for line in path.read_text(encoding='utf-8').split('\n'):
        m = re.match(r'^\| \[([^\]]+)\]\((?:\.\./)+Players/([^)]+)\.md\) \|(.*)$', line)
        if m: out[m.group(2)] = [c.strip() for c in m.group(3).strip().strip('|').split('|')]
    return out
COLS = ['Age','Club','Lg','Pos','G','GS','MP','FG','FGA','FG%','3P','3PA','3P%','2P','2PA','2P%','eFG%','FT','FTA','FT%','ORB','DRB','TRB','AST','STL','BLK','TOV','PF','PTS','TS%']
def pct(v): return 'N/A' if v == 'N/A' else f'{float(v):.1%}'
for season in ('2003-04', '2004-05'):
    pg = page_rows(L/season/'League_Stats.md')
    n = 0; bad = []; missing = []
    for rid, c in cards.items():
        t = next(t for t in c['tables'] if t[0] == '## Regular-season statistics by year')
        row = next((r for r in t[2] if r[0] == season), None)
        pr = pg.get(rid)
        if pr is None:
            if row: missing.append(rid)
            continue
        d = dict(zip(COLS, pr))
        if row is None:
            if d['G'] not in ('0', 'N/A'): bad.append((rid, 'no card row but page G', d['G']))
            continue
        n += 1
        exp = [d['G'], d['GS'], d['MP'], d['PTS'], d['TRB'], d['AST'], d['STL'], d['BLK'], d['TOV'], pct(d['FG%']), pct(d['3P%']), pct(d['FT%'])]
        if row[2:] != exp: bad.append((rid, row[2:], exp))
    print(season, 'compared', n, 'bad', len(bad), 'card rows without page row', missing[:5])
    for b in bad[:10]: print('  ', b)
