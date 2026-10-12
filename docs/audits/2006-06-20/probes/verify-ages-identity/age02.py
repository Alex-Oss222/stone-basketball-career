import json
R='/home/user/stone-basketball-career'
for s in ('2003-04','2004-05','2005-06'):
    d=json.load(open(f'{R}/career/Dwyane_Wade/{s}/00_Team/Team/Roster/roster.json'))
    ps=d.get('players') or d.get('roster')
    print(s, len(ps), list(d.keys())[:10])
    for p in ps:
        if not p.get('date_of_birth'):
            print('  missing', p.get('name'), p.get('bbr_id') or p.get('player_id'), {k:p[k] for k in p if 'birth' in k}, p.get('status') or p.get('roster_status'))
