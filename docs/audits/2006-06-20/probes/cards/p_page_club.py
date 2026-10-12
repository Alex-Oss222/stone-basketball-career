import sys, json, re, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime.league_cards import _code
ROOT = Path('/home/user/stone-basketball-career')
L = ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League'
reg = {p['registry_id']: p for p in json.load(open(L/'player_registry.json'))['players']}
truth = pickle.load(open('truth.pkl','rb'))
lines = pickle.load(open('lines_2005_06.pkl','rb'))
def page_rows(path):
    out = {}
    for line in path.read_text(encoding='utf-8').split('\n'):
        m = re.match(r'^\| \[([^\]]+)\]\((?:\.\./)+Players/([^)]+)\.md\) \|(.*)$', line)
        if m: out[m.group(2)] = [c.strip() for c in m.group(3).strip().strip('|').split('|')]
    return out
pg = page_rows(L/'2005-06/League_Stats.md')
c = collections.Counter(); ex = []
for rid, cells in pg.items():
    p = reg[rid]
    src = (p.get('team_code') or '') + (' rights' if p.get('cohort') == '2003_draft_rights' else '')
    cell = cells[1]
    played = {('MIA' if r['team']=='Miami Heat' else _code(r['team'], {}, p)) for r in lines.get(rid, []) if r.get('appearance')}
    if cell in (p.get('team_code'), src): c['equals registry 2002-03/source code'] += 1
    else: c['other'] += 1; ex.append((rid, cell, p.get('team_code')))
    if played and cell not in played: c['cell is a club he never played for in 2005-06'] += 1
print(c); print(ex[:10])
# examples
for rid in ('stockjo01','jordami01','willial02','jonesju01','cartean01'):
    if rid in pg: print(rid, reg[rid]['name'], 'page cell:', pg[rid][1], '| G', pg[rid][4], '| club_truth 2006-06-20:', truth[rid][0])
