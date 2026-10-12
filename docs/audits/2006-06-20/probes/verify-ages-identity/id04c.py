import sys, json, collections, re
sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime import player_contracts as pc
R='/home/user/stone-basketball-career'
cat=pc.build_contract_catalog(R, 'career/Dwyane_Wade')
ps=cat['players']
undert={'under_contract','under_contract_unverified','minimum_contract_unverified','under_rookie_contract','under_contract_guarantee_amended'}
sel=[p for p in ps if p['status'] in undert and p['current'] is None]
print('under-type & no current:', len(sel), collections.Counter(p['status'] for p in sel))
led=collections.defaultdict(list)
for s in ('2004-05','2005-06'):
    for c in json.load(open(f'{R}/career/Dwyane_Wade/{s}/League/contracts.json'))['contracts']:
        led[c.get('bbr_id')].append((s,c))
inv=json.load(open(R+'/library/2003/league/nba_2003_contracts.json'))
invp={}
for k,v in inv.items():
    if isinstance(v,list) and v and isinstance(v[0],dict) and 'bbr_id' in v[0]:
        for c in v: invp.setdefault(c['bbr_id'],[]).append(c)
    if isinstance(v,dict):
        for kk,vv in v.items():
            if isinstance(vv,list) and vv and isinstance(vv[0],dict) and ('bbr_id' in vv[0] or 'player' in vv[0]):
                for c in vv: invp.setdefault(c.get('bbr_id'),[]).append(c)
print('inventory players', len(invp))
def seasons_of(sched):
    return [s for s,a in (sched or {}).items() if a]
out=collections.Counter(); later=[]; rows=[]
for p in sel:
    b=p['identity'].get('bbr_id') or p['id']
    ss=set(seasons_of(p['control'].get('schedule')))
    for s,c in led.get(b,[]): ss|=set(seasons_of(c.get('schedule')))
    for c in invp.get(b,[]): ss|=set(seasons_of(c.get('schedule') or c.get('salaries')))
    for h in p['history']:
        for k in ('schedule','seasons','salary_by_season'):
            if isinstance(h.get(k),dict): ss|=set(seasons_of(h[k]))
        if h.get('end_season'): ss.add(h['end_season'])
    mx=max(ss) if ss else None
    rows.append((p['id'],p['status'],mx, [ (h.get('start_season'),h.get('end_season'),h.get('expiry_date'),h.get('status')) for h in p['history']][:3]))
    if mx and mx>='2005-06': later.append(p['id'])
print('with salary season >= 2005-06:', len(later))
c2=collections.Counter(r[2] for r in rows); print(c2)
for r in rows:
    if r[2] and r[2]>='2005-06': print(r)
json.dump(rows, open('id04_rows.json','w'), indent=1, default=str)
