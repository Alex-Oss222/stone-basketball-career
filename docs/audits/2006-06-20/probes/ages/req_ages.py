import json, glob, collections, sys
sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime.league_cards import age_on
ROOT='/home/user/stone-basketball-career'
reg={p['name']:p for p in json.load(open(ROOT+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
none=collections.defaultdict(list); wrong=[]; n=0
for f in sorted(glob.glob(ROOT+'/career/Dwyane_Wade/*/0[68]_*/**/Game_*.request.json',recursive=True)):
    d=json.load(open(f)); fr=d.get('frozen')
    if not fr: continue
    n+=1
    date=d.get('game_date') or d.get('date')
    for side in ('home','away'):
        s=fr.get(side) or {}
        if d[side].get('team')!='Miami Heat': continue
        for p in s.get('players',[]):
            nm=p.get('player_id') or p.get('name')
            if p.get('age') is None: none[nm].append(date)
            else:
                b=reg.get(nm,{}).get('birth_date') if nm!='Dwyane Wade' else '1984-01-17'
                if b and age_on(b,date)!=p['age']: wrong.append((f.split('Dwyane_Wade/')[1],nm,p['age'],age_on(b,date)))
print('requests with frozen',n)
for k,v in none.items(): print(k,len(v),min(v),max(v), sum(1 for x in v if x<'2005-01-01'),'before injury pause', 'registry birth', reg.get(k,{}).get('birth_date'))
print('wrong',wrong[:10],len(wrong))
