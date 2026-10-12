import json
R='/home/user/stone-basketball-career'
for s in ['2003-04','2004-05','2005-06']:
    d=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/season_awards.json'))
    for x in d['decisions']:
        E=x.get('electorate'); B=x.get('ballot')
        if 'tally' in x:
            T=x['tally']
            tot=sum(t['points'] for t in T)
            exp=E*sum(B)
            if x['award']=='finals_mvp': exp=E*B[0]
            if tot!=exp: print(s,x['id'],'points sum',tot,'expected',exp)
            for i in range(len(B)):
                sp=sum(t['votes_by_place'][i] for t in T)
                if sp!=E: print(s,x['id'],'place',i+1,'votes',sp,'electorate',E)
            for t in T:
                if sum(v*b for v,b in zip(t['votes_by_place'],B))!=t['points']: print(s,x['id'],'points calc',t)
                if t['first_place']!=t['votes_by_place'][0]: print(s,x['id'],'first place',t)
            srt=sorted(T,key=lambda t:(-t['points'],-t['first_place']))
            if [t.get('player',t.get('coach')) for t in srt]!=[t.get('player',t.get('coach')) for t in T]: print(s,x['id'],'tally order differs')
            top=[t for t in T if (t['points'],t['first_place'])==(T[0]['points'],T[0]['first_place'])]
            if sorted(t.get('player',t.get('coach')) for t in top)!=sorted(x['winners']): print(s,x['id'],'winners',x['winners'],'top',[t.get('player') for t in top])
        else:
            print(s,x['id'],'keys',[k for k in x if k not in('id','award','name')], 'teams type',type(x.get('teams')))
