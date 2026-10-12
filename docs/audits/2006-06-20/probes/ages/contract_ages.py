import json, re, sys, glob, collections
sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime.league_cards import age_on
ROOT='/home/user/stone-basketball-career'
reg={p['registry_id']:p for p in json.load(open(ROOT+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
recs=json.load(open('birth_records.json'))
anyb=collections.defaultdict(set)
for r in recs:
    if r['bbr'] and '/fiba' not in r['file']: anyb[r['bbr']].add((r['birth'],r['file']))
bad=[]; na=[]; n=0; teamstat=collections.Counter(); fa_uc=[]
dec=json.JSONDecoder()
for f in sorted(glob.glob(ROOT+'/career/Dwyane_Wade/Contracts/players/*.html')):
    pid=f.split('/')[-1][:-5]
    h=open(f).read()
    i=h.find('"identity": {')
    if i<0: continue
    idn,_=dec.raw_decode(h[i+len('"identity": '):])
    n+=1
    age=idn.get('age'); cut=idn.get('cutoff')
    teamstat[(idn.get('team')=='Free agent', idn.get('status'))]+=1
    if idn.get('team')=='Free agent' and idn.get('status') in ('under_contract',): fa_uc.append(pid)
    p=reg.get(pid)
    b=(p or {}).get('birth_date')
    if pid=='wadedw01': b='1984-01-17'
    if b:
        e=age_on(b,cut)
        if e!=age: bad.append((pid,age,e,b,cut))
    else:
        na.append((pid,age,idn.get('name'),sorted(anyb.get(pid) or [])))
print('pages',n,'bad',len(bad),bad[:5]); print('no registry birth',len(na))
for x in na: print(x)
print(teamstat)
print('FA + under_contract', len(fa_uc), fa_uc[:30])
