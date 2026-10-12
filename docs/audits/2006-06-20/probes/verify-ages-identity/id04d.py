import sys, json, collections, glob
sys.path.insert(0,'/home/user/stone-basketball-career')
R='/home/user/stone-basketball-career'
rows=json.load(open('id04_rows.json'))
inv=json.load(open(R+'/library/2003/league/nba_2003_contracts.json'))
invp=collections.defaultdict(list)
for club,e in inv['clubs'].items():
    for c in e['players']: invp[c.get('bbr_id')].append(c)
led=collections.defaultdict(list)
for s in ('2004-05','2005-06'):
    for c in json.load(open(f'{R}/career/Dwyane_Wade/{s}/League/contracts.json'))['contracts']:
        led[c.get('bbr_id')].append((s,c))
# In-season 2005-06 league moves: find signings
mv=json.load(open(f'{R}/career/Dwyane_Wade/2004-05/League/league_moves.json'))
print('league_moves keys', list(mv.keys())[:8])
res=collections.Counter(); final=[]
for pid,status,mx,hist in rows:
    ss=set()
    for c in invp.get(pid,[]): ss|={s for s,a in (c.get('schedule') or {}).items() if a}
    for s,c in led.get(pid,[]): ss|={k for k,a in (c.get('schedule') or {}).items() if a}
    m=max([x for x in [mx]+sorted(ss) if x] or [None])
    final.append((pid,status,m,mx))
    res[m]+=1
print(res)
for f in final:
    if f[2] and f[2]>='2005-06': print(f)
