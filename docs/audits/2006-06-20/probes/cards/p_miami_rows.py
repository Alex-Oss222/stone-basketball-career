import sys, json, re, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
MC = ROOT / 'career/Dwyane_Wade/2005-06/00_Team/Team/Player_Cards'
cards = pickle.load(open('cards.pkl','rb'))
lines = pickle.load(open('lines_2005_06.pkl','rb'))
roster = json.load(open(ROOT/'career/Dwyane_Wade/2005-06/00_Team/Team/Roster/roster.json'))['players']
reg = {p['registry_id']: p for p in json.load(open(ROOT/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
bybbr = {p.get('bbr_id'): k for k, p in reg.items()}
for p in roster:
    f = MC / Path(p.get('player_card','')).name
    if not f.is_file(): continue
    t = f.read_text(encoding='utf-8')
    m = re.search(r'^\| 2005-06 \|([^\n]*)$', t, re.M)
    mrow = [c.strip() for c in m.group(1).strip().strip('|').split('|')] if m else None
    rid = bybbr.get(p.get('bbr_id')) or ('wadedw01' if p['name']=='Dwyane Wade' else None)
    # league: aggregate MIA records only
    recs = [r for r in lines.get(rid, []) if r['team']=='Miami Heat' and r.get('appearance')]
    g = len(recs)
    lc = None
    if rid in cards:
        tt = next(x for x in cards[rid]['tables'] if x[0] == '## Regular-season statistics by year')
        lc = next((r for r in tt[2] if r[0]=='2005-06'), None)
    print(p['name'], '| miami card:', mrow[:6] if mrow else None, '| MIA appearances:', g, '| league card:', lc[1:6] if lc else None)
