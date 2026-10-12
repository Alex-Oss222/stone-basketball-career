import sys, json, pickle, collections
from datetime import date
sys.path.insert(0, '/home/user/stone-basketball-career')
ROOT='/home/user/stone-basketball-career'
cards = pickle.load(open('cards.pkl','rb'))
reg = {p['registry_id']: p for p in json.load(open(ROOT+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
def age(b, on):
    b = date.fromisoformat(b); d = date.fromisoformat(on)
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))
bad = []; na = []
for rid, c in cards.items():
    b = reg[rid].get('birth_date')
    if not b: na.append(rid); continue
    if str(age(b, '2006-06-20')) != c['age']: bad.append((rid, c['age'], age(b, '2006-06-20')))
print('bad', bad, 'no birth', na)
# Wade's birth vs identity
idn = json.load(open(ROOT+'/career/Dwyane_Wade/professional_identity.json'))
print('wade registry birth', reg['wadedw01'].get('birth_date'), 'identity', idn.get('birth_date') or idn.get('date_of_birth'), 'card age', cards['wadedw01']['age'])
# cross-check registry births vs Miami register births
for s in ('2005-06',):
    r = json.load(open(f'{ROOT}/career/Dwyane_Wade/{s}/00_Team/Team/Roster/roster.json'))['players']
    for p in r:
        rid = next((k for k, v in reg.items() if v.get('bbr_id') and v['bbr_id'] == p.get('bbr_id')), None)
        if rid and p.get('date_of_birth') and reg[rid].get('birth_date') != p['date_of_birth']:
            print('birth mismatch', p['name'], reg[rid]['birth_date'], p['date_of_birth'])
births = json.load(open(ROOT+'/library/careers/nba_player_births.json'))['players']
mm = [(k, reg[k]['birth_date'], v['birth_date']) for k, v in births.items() if k in reg and v.get('birth_date') and reg[k].get('birth_date') and reg[k]['birth_date'] != v['birth_date']]
print('registry vs researched births mismatches', len(mm), mm[:5])
