import json, glob, os
R='/home/user/stone-basketball-career'
base=f'{R}/career/Dwyane_Wade/FIBA/Continental_Cups/2005'
t=json.load(open(f'{base}/tournament.json'))
res={}
for p in glob.glob(f'{base}/Games/*.result.json'):
    d=json.load(open(p)); res[d['event_id']]=d
print('results',len(res),'games',len(t['games']))
# map game number -> result by date/home/away
by={}
for d in res.values():
    by[(d['game_date'],d['home'],d['away'])]=d
from collections import defaultdict
stage_games=defaultdict(list)
for n,g in t['games'].items():
    d=by.get((g['date'],g['home'],g['away']))
    if d is None:
        # maybe slot-resolved names
        cand=[x for x in res.values() if x['event_id'].endswith(f'g{int(n):02d}')]
        d=cand[0] if cand else None
    if d is None: print('no result for game',n,g); continue
    stage_games[g['stage']].append(d)
for grp,rows in t['tables'].items():
    stage=t['groups'][grp]['stage']
    games=list(stage_games[stage])
    teams=[r['team'] for r in rows]
    # carry_from: in round R, results of carried games among qualifiers count
    for src in t['groups'][grp]['carry_from']:
        sg=t['groups'][src]['stage']
        games+= [d for d in stage_games[sg] if d['home'] in teams and d['away'] in teams]
    tab={tm:dict(w=0,l=0,pf=0,pa=0) for tm in teams}
    for d in games:
        h,a=d['home'],d['away']; hs,as_=d['final_score']['home'],d['final_score']['away']
        if h not in tab or a not in tab: continue
        tab[h]['pf']+=hs;tab[h]['pa']+=as_;tab[a]['pf']+=as_;tab[a]['pa']+=hs
        if hs>as_: tab[h]['w']+=1;tab[a]['l']+=1
        else: tab[a]['w']+=1;tab[h]['l']+=1
    for r in rows:
        x=tab[r['team']]
        if (x['w'],x['l'],x['pf'],x['pa'])!=(r['w'],r['l'],r['pf'],r['pa']) or r['pts']!=2*x['w']+x['l']:
            print(grp,r['team'],'shown',(r['w'],r['l'],r['pf'],r['pa'],r['pts']),'recomputed',x)
    print(grp,'checked',len(rows),'games',len(games))
print(t['ranking'])
print({k:v for k,v in t['games'].items() if not v['stage'].startswith('group')})
