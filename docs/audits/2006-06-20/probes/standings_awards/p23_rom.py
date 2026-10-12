import json
R='/home/user/stone-basketball-career'
careers=json.load(open(f'{R}/library/careers/nba_player_careers.json'))['players']
reg=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))
reg=reg['players'] if isinstance(reg,dict) else reg
n2b={p['name']:p.get('bbr_id') for p in reg}
for s in ['2003-04','2004-05','2005-06']:
    dec=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/award_decisions.json'))['decisions']
    for d in dec:
        if d['award']!='rookie_of_month': continue
        for x in d['shortlist']:
            b=n2b.get(x['player'])
            first=min((careers.get(b) or {}).get('seasons') or {'?':0}) if b else None
            if first!=s and not (x['player']=='Dwyane Wade' and s=='2003-04'): print(s,d['id'],x['player'],b,'first season',first)
    # also all-star rookie challenge rookies/sophomores
    a=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/all_star.json'))
    rc=[x for x in a['steps'] if x['step']=='rookie_challenge'][0]['teams']
    y=int(s[:4])
    prev=f'{y-1}-{str(y)[-2:]}'
    for team,ps in rc.items():
        for p in ps:
            b=p.get('bbr_id'); first=min((careers.get(b) or {}).get('seasons') or {'?':0}) if b else None
            want=s if team=='Rookies' else prev
            if first!=want and p['player']!='Dwyane Wade': print(s,'RC',team,p['player'],b,'first',first,'want',want)
    print(s,'done')
