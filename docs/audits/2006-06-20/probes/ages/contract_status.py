import json,collections
R='/home/user/stone-basketball-career/'
c=json.load(open(R+'career/Dwyane_Wade/Contracts/catalog.json'))
led={}
for s in ('2004-05','2005-06'):
    for e in json.load(open(R+f'career/Dwyane_Wade/{s}/League/contracts.json'))['contracts']:
        led.setdefault(e['bbr_id'],[]).append(e['schedule'])
moves=json.load(open(R+'career/Dwyane_Wade/2005-06/League/league_moves.json'))['entries']
mv=collections.defaultdict(list)
for x in moves: mv[x.get('bbr_id')].append((x['date'],x['kind'],(x.get('contract') or {}).get('until')))
stale=[]
for p in c['players']:
    if p['status'] in ('under contract','under rookie contract','under contract unverified','minimum contract unverified') and p['current_contract_id'] is None:
        cov=any(any(k>='2005-06' and v for k,v in s.items()) for s in led.get(p['player_id'],[]))
        if not cov: stale.append((p['player_id'],p['name'],p['status'],p['team'],mv.get(p['player_id'],[])[-1:] ))
print(len(stale)); print(collections.Counter(s[2] for s in stale)); print(sum(1 for s in stale if s[4]),'with a 2005-06 in-season deal ending', {s[4][0][2] for s in stale if s[4]})
for s in stale[:12]: print(s)
