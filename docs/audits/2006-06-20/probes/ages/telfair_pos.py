import json,glob
R='/home/user/stone-basketball-career/'
reg={p['bbr_id']:p for p in json.load(open(R+'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players'] if p.get('bbr_id')}
t=reg['telfase01']; print('registry',t['position'],t.get('position_before'),t.get('position_corrected_on'),t.get('position_basis'))
r=[p for p in json.load(open(R+'career/Dwyane_Wade/2005-06/00_Team/Team/Roster/roster.json'))['players'] if p.get('bbr_id')=='telfase01'][0]
print('register',r['positions'],r['working_role'])
tot=after=0
for f in sorted(glob.glob(R+'career/Dwyane_Wade/2005-06/0[68]_*/**/Game_*.request.json',recursive=True)):
    d=json.load(open(f)); day=d.get('game_date') or d.get('date'); side='home' if d['home'].get('team')=='Miami Heat' else 'away'
    if any(p.get('player_id')=='Sebastian Telfair' and p.get('position')=='SF' for p in d.get('frozen',{}).get(side,{}).get('players',[])):
        tot+=1; after+=day>=t['position_corrected_on']
print('requests with Telfair at SF',tot,'on/after correction',after)
