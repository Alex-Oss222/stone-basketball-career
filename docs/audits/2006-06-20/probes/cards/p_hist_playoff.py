import sys, json, re, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime.write_back import _key
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
L = ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League'
reg = {p['registry_id']: p for p in json.load(open(L/'player_registry.json'))['players']}
cards = pickle.load(open('cards.pkl','rb'))
def pct(s): return 'N/A' if s == 'N/A' else f'{float(s):.1%}'
for season in ('2003-04','2004-05'):
    p = L/season/'Playoffs/Playoff_Stats.md'
    if not p.is_file(): print('no page', p); continue
    sec = p.read_text(encoding='utf-8').split('## All playoff games')[1].split('\n## ')[0]
    rows = {}
    for line in sec.split('\n'):
        if line.startswith('| ') and not line.startswith('| Player') and not line.startswith('| ---'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            rows.setdefault(_key(re.sub(r'^\[([^\]]+)\].*$', r'\1', cells[0])), []).append(cells)
    bad = []; n = 0; seen = set()
    for rid, c in cards.items():
        t = next(t for t in c['tables'] if t[0] == '## Playoff statistics by year')
        row = next((r for r in t[2] if r[0] == season), None)
        k = _key(reg[rid]['name'])
        prs = rows.get(k)
        if row is None:
            continue
        seen.add(k)
        if not prs: bad.append((rid, 'card row, no page row')); continue
        pr = prs[0]; n += 1
        exp = [pr[2], pr[3], pr[4], pr[5], pr[6], pr[7], pr[8], pr[9], pr[10], pct(pr[12]), pct(pr[14]), pct(pr[16])]
        if row[2:] != exp or len(prs) > 1 or row[1] != pr[1]: bad.append((rid, row[1:], [x[1] for x in prs], exp))
    notseen = [k for k in rows if k not in seen]
    print(season, 'compared', n, 'bad', len(bad), 'page players without card row', len(notseen), notseen[:10])
    for b in bad[:8]: print('  ', b)
