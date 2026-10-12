import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
from p01_standings import results
R='/home/user/stone-basketball-career'
RULES={'2003-04':'library/2003/league/nba_2003_04_playoff_rules.json','2004-05':'library/2004/league/nba_2004_05_playoff_rules.json','2005-06':'library/2005/league/nba_2005_06_playoff_rules.json'}
for s,rp in RULES.items():
    rules=json.load(open(f'{R}/{rp}'))
    where={c:(conf,div) for conf,divs in rules['divisions'].items() if conf in('East','West') for div,cl in divs.items() for c in cl}
    games=[]
    for d in results(s).values():
        hw=d['final_score']['home']>d['final_score']['away']
        games.append((d['home'],d['away'],d['home'] if hw else d['away'],d['final_score']['home']-d['final_score']['away']))
    def rec(c,ag=None):
        w=l=0
        for h,a,win,_ in games:
            if c not in(h,a):continue
            o=a if c==h else h
            if ag is not None and o not in ag: continue
            if win==c: w+=1
            else: l+=1
        return w,l
    def pct(c,ag=None):
        w,l=rec(c,ag); return w/(w+l) if w+l else 0
    print(s)
    for c in sorted(where):
        if c not in {x for g in games for x in g[:2]}: print(' missing club in results', c)
    # division winners by plain record (print ties)
    for conf,divs in rules['divisions'].items():
        if conf not in('East','West'):continue
        for div,cl in divs.items():
            o=sorted(cl,key=lambda c:-pct(c))
            note=''
            if pct(o[0])==pct(o[1]): note=f' TIE with {o[1]} h2h {rec(o[0],{o[1]})} divrec {rec(o[0],set(cl)-{o[0]})} vs {rec(o[1],set(cl)-{o[1]})} confrec {rec(o[0],{x for x in where if where[x][0]==conf}-{o[0]})} vs {rec(o[1],{x for x in where if where[x][0]==conf}-{o[1]})}'
            print(' ',conf,div,[(c,rec(c)) for c in o[:2]],note)
    pj=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/playoffs.json'))
    for conf,rows in pj['seeds'].items():
        for r in rows:
            if (r['wins'],r['losses'])!=rec(r['club']): print(' seed rec mismatch',r)
    # ties among seeds
    for conf in('East','West'):
        confclubs={x for x in where if where[x][0]==conf}
        o=sorted(confclubs,key=lambda c:-pct(c))
        for a,b in zip(o,o[1:]):
            if pct(a)==pct(b):
                print('  tie',a,b,rec(a),'h2h',rec(a,{b}),'conf',rec(a,confclubs-{a}),rec(b,confclubs-{b}), 'div', where[a][1],where[b][1])
