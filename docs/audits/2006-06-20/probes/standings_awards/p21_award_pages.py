import json, os, re
R='/home/user/stone-basketball-career'
for s in ['2003-04','2004-05','2005-06']:
    dec=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/award_decisions.json'))['decisions']
    bad=0
    for d in dec:
        p=f"{R}/{d['filed_on']}"
        if not os.path.isfile(p): print(s,'missing page',d['filed_on']); continue
        t=open(p).read()
        for x in d['shortlist']:
            ev=(f"{x['games']} G, {x['wins']}-{x['losses']} in his games, {x['pts']} PTS, {x['reb']} REB, {x['ast']} AST, Game Score {x['game_score']} a game; score {x['score']}")
            if ev not in t or x['player'] not in t: bad+=1; print(s,d['id'],x['player'],'row not on page')
        # filed bucket check
        e=d['period_end']; m=int(e[5:7]); day=int(e[8:10])
        if d['award']=='player_of_week':
            wk=1 if day<=7 else 2 if day<=14 else 3 if day<=21 else 4
            if f'Week_{wk}/' not in d['filed_on']: print(s,d['id'],'filed',d['filed_on'])
        mm={10:'10_October',11:'11_November',12:'12_December',1:'01_January',2:'02_February',3:'03_March',4:'04_April'}[m]
        if f'/{mm}/' not in d['filed_on']: print(s,d['id'],'month bucket',d['filed_on'])
    print(s,len(dec),'decisions; rows missing',bad)
    # month page counts
