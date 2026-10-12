import json, glob, collections, sys
sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime.league_cards import age_on
R='/home/user/stone-basketball-career/career/Dwyane_Wade'
reg={p['name']:p.get('birth_date') for p in json.load(open(R+'/Stats_and_Awards/League/player_registry.json'))['players']}
nulls=collections.Counter(); dates=collections.defaultdict(list); total_req=collections.Counter(); wrong=[]
for s in ('2004-05','2005-06'):
    files=glob.glob(f'{R}/{s}/**/Game_*.request.json', recursive=True)
    for f in files:
        d=json.load(open(f))
        fr=d.get('frozen')
        if not fr: continue
        side='home' if d['home'].get('team')=='Miami Heat' else 'away' if d['away'].get('team')=='Miami Heat' else None
        if not side: continue
        total_req[s]+=1
        reqnull=False
        for p in fr[side]['players']:
            nm=p['player_id']
            if p.get('age') is None:
                nulls[(s,nm)]+=1; dates[(s,nm)].append(d['game_date'])
            else:
                b=reg.get(nm) if nm!='Dwyane Wade' else '1984-01-17'
                if b and age_on(b,d['game_date'])!=p['age']: wrong.append((f,nm,p['age'],age_on(b,d['game_date'])))
print(total_req)
for k,v in sorted(nulls.items()): print(k, v, min(dates[k]), max(dates[k]), 'pre-pause', sum(1 for x in dates[k] if x<'2005-01-01'))
print('wrong non-null', len(wrong), wrong[:5])
# requests with any null
print('Wright from 2004-11-03:', sum(1 for x in dates[('2004-05','Dorell Wright')] if x>='2004-11-03'))
print('distinct requests with any null:', len({(s,x) for (s,n),l in dates.items() for x in l}))
