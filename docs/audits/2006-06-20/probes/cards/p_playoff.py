import sys, json, re, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime.write_back import _key
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
L = ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League'
reg = {p['registry_id']: p for p in json.load(open(L/'player_registry.json'))['players']}
cards = pickle.load(open('cards.pkl','rb'))
text = (L/'2005-06/Playoffs/Playoff_Stats.md').read_text(encoding='utf-8')
sec = text.split('## All playoff games')[1].split('\n## ')[0]
rows = {}
dups = []
for line in sec.split('\n'):
    if line.startswith('| ') and not line.startswith('| Player') and not line.startswith('| ---'):
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        name = re.sub(r'^\[([^\]]+)\].*$', r'\1', cells[0])
        k = _key(name)
        if k in rows: dups.append(name)
        rows.setdefault(k, []).append(cells)
print('page rows', sum(len(v) for v in rows.values()), 'dup names', dups)
def pct(s):
    return 'N/A' if s == 'N/A' else f'{float(s):.1%}'
mism = []; matched = 0; card_only = []; 
seen = set()
for rid, c in cards.items():
    t = next(t for t in c['tables'] if t[0] == '## Playoff statistics by year')
    row = next((r for r in t[2] if r[0] == '2005-06'), None)
    if row is None: continue
    k = _key(reg[rid]['name'])
    prs = rows.get(k)
    if row[2] == '0':
        if prs: mism.append((rid, 'card shows 0 G but page has', prs[0][:4]))
        continue
    if not prs: card_only.append((rid, row[:4])); continue
    seen.add(k)
    # aggregate page rows if multiple clubs
    pr = prs[0]
    if len(prs) > 1: mism.append((rid, 'multiple page rows', [p[:3] for p in prs])); continue
    exp = [pr[2], pr[3], pr[4], pr[5], pr[6], pr[7], pr[8], pr[9], pr[10], pct(pr[12]), pct(pr[14]), pct(pr[16])]
    got = row[2:]
    if exp != got or row[1] != pr[1]:
        mism.append((rid, reg[rid]['name'], 'card', row[1:], 'page', pr[1], exp))
    else: matched += 1
print('matched', matched, 'mismatches', len(mism), 'card-only', card_only)
for m in mism[:20]: print('  ', m)
page_only = [k for k in rows if k not in seen]
print('page rows with no card playoff row', len(page_only), page_only[:20])
