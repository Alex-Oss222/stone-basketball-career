import json, glob, collections, sys
sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime.league_cards import age_on
R='/home/user/stone-basketball-career/career/Dwyane_Wade'
reg={p['name']:p.get('birth_date') for p in json.load(open(R+'/Stats_and_Awards/League/player_registry.json'))['players']}
nulls=collections.Counter(); reqs=collections.defaultdict(set); dates=collections.defaultdict(list); wrong=0
for s in ('2004-05','2005-06'):
    for f in glob.glob(f'{R}/{s}/0[68]_*/**/Game_*.request.json', recursive=True):
        d=json.load(open(f))
        fr=d.get('frozen')
        if not fr: continue
        for side in ('home','away'):
            t=fr[side]
            if t.get('team','')!='Miami Heat' and 'Miami' not in json.dumps(t.get('team','')) and 'MIA' not in json.dumps(t.get('club','')):
                # determine Miami side
                pass
        for side in ('home','away'):
            for p in fr[side]['players']:
                nm=p.get('player_id') or p.get('name')
                if p.get('age') is None:
                    nulls[(s,nm)]+=1; reqs[(s,nm)].add(f); dates[(s,nm)].append(d['game_date'])
for k,v in sorted(nulls.items()): print(k, v, min(dates[k]), max(dates[k]))
print(list(fr['home'].keys()))
