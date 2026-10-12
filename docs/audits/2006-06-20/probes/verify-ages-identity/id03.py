import json, glob, collections
R='/home/user/stone-basketball-career/career/Dwyane_Wade'
c=collections.Counter(); dates=[]
for f in glob.glob(f'{R}/2005-06/**/Game_*.request.json', recursive=True):
    d=json.load(open(f))
    fr=d.get('frozen')
    side='home' if d['home'].get('team')=='Miami Heat' else 'away' if d['away'].get('team')=='Miami Heat' else None
    if not side: continue
    for src in ([fr[side]['players']] if fr else [])+[d[side].get('players') or []]:
        pass
    pos=set()
    if fr:
        for p in fr[side]['players']:
            if p['player_id']=='Sebastian Telfair': pos.add(('frozen',p.get('position')))
    for p in d[side].get('players') or []:
        if p['player_id']=='Sebastian Telfair': pos.add(('req',p.get('position')))
    if pos:
        c[tuple(sorted(pos))]+=1; dates.append((d['game_date'],tuple(sorted(pos))))
print(c)
print(sum(1 for x,p in dates if x>='2005-12-31' and ('frozen','SF') in p), 'on/after 2005-12-31 frozen SF')
print(min(dates), max(dates))
# rotations
for f in sorted(glob.glob(f'{R}/2005-06/00_Team/Team/Depth_Chart/**/rotation.json', recursive=True)):
    d=json.load(open(f))
    for p in d['players']:
        if p['player_id']=='Sebastian Telfair': print(f.split('2005-06/')[1], p.get('position'), p.get('minutes'))
