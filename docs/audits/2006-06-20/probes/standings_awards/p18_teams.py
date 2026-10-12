import json
from collections import Counter
R='/home/user/stone-basketball-career'
for s in ['2003-04','2004-05','2005-06']:
    sa=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/season_awards.json'))
    for x in sa['decisions']:
        if 'teams' not in x: continue
        E=x['electorate'];B=x['ballot']
        allp=[p for t in x['teams'] for p in t['players']]
        tot=sum(p['points'] for p in allp)+sum(o['points'] for o in x['others'])
        exp=E*5*sum(B)
        pos=[Counter(p.get('position') for p in t['players']) for t in x['teams']]
        sizes=[len(t['players']) for t in x['teams']]
        print(s,x['award'],'electorate',E,'ballot',B,'points total',tot,'expected',exp,'sizes',sizes,'pos',[dict(c) for c in pos] if x['award']!='all_rookie' else '')
        # ordering: every team-1 player >= team-2 players within same position group
        names=[p['player'] for p in allp]+[o['player'] for o in x['others']]
        dup=[n for n,c in Counter(names).items() if c>1]
        if dup: print('   duplicate',dup)
        for t in x['teams']:
            for p in t['players']:
                if x['award']=='all_rookie' and p.get('games',99)<30: print('   all-rookie games<30',p['player'])
                if x['award'] in('all_nba','all_defensive') and p.get('games',99)<55: print('   <55 games',p['player'],p.get('games'))
                if x['award']=='all_defensive' and p.get('mpg',99)<24: print('   mpg<24',p['player'])
