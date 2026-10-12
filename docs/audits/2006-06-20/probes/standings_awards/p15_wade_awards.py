import json, os
R='/home/user/stone-basketball-career'
aw={a['id']:a for a in json.load(open(f'{R}/career/Dwyane_Wade/awards.json'))['awards']}
seen=set()
W='Dwyane Wade'
for s in ['2003-04','2004-05','2005-06']:
    L=f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}'
    for d in json.load(open(f'{L}/award_decisions.json'))['decisions']:
        if d['winner']==W:
            a=aw.get(d['id']); seen.add(d['id'])
            if not a: print('missing in awards.json',d['id']); continue
            for k1,k2 in (('period_start','period_start'),('period_end','period_end'),('announced_on','awarded_on')):
                if d[k1]!=a[k2]: print('date mismatch',d['id'],k1,d[k1],a[k2])
            src='career/Dwyane_Wade/'+a['source'].split('#')[0]
            if src!=d['filed_on']: print('source vs filed_on',d['id'],src,d['filed_on'])
            if not os.path.isfile(f'{R}/{src}'): print('source missing',src)
    sa=json.load(open(f'{L}/season_awards.json'))
    for d in sa['decisions']:
        if W in (d.get('winners') or []):
            # find id
            cand=[k for k in aw if k==d['id']]
            if not cand: print('season award missing',d['id'])
            else:
                seen.add(d['id']); a=aw[d['id']]
                if a['awarded_on']!=d['announced_on']: print('season date',d['id'],a['awarded_on'],d['announced_on'])
        for t in d.get('teams') or []:
            if any(p['player']==W for p in t['players']):
                key=f"{d['id']}-{t['team'].split()[0].lower()}"
                if key not in aw: print('team award missing',key,[k for k in aw if k.startswith(d['id'])])
                else:
                    seen.add(key)
                    if aw[key]['awarded_on']!=d['announced_on']: print('team date',key,aw[key]['awarded_on'],d['announced_on'])
                    if t['team'].split()[0] not in aw[key]['name']: print('team name',key,aw[key]['name'],t['team'])
    a=json.load(open(f'{L}/all_star.json'))
    for x in a['all_stars']:
        if x['player']==W:
            k=f'{s}-all-star'; seen.add(k)
            if k not in aw: print('all-star missing',s)
            elif aw[k]['awarded_on']!=x['selected_on']: print('all-star date',s,aw[k]['awarded_on'],x['selected_on'])
    g=json.load(open(f'{L}/all_star_games.json'))
    for gk,gg in g['games'].items():
        if W in gg['mvp']['winners']:
            k=[x for x in aw if x.startswith(s) and 'mvp' in x and ('rookie' in x or 'all-star' in x)]
            print(s,gk,'Wade MVP; awards ids',k); seen.update(k)
            for kk in k: print('   ',aw[kk]['period_start'],gg['date'],aw[kk]['awarded_on'],gg['mvp']['decided_on'],aw[kk].get('recorded_on'),gg['mvp'].get('recorded_on'))
print('awards.json entries not matched to a record:',sorted(set(aw)-seen))
