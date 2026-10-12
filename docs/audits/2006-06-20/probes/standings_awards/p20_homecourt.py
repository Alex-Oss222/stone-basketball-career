import json, sys, io, contextlib
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import table
R='/home/user/stone-basketball-career'
for s in ['2003-04','2004-05','2005-06']:
    t,_=table(s)
    pj=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/playoffs.json'))
    seed={r['club']:r['seed'] for rows in pj['seeds'].values() for r in rows}
    for se in pj['series']:
        a,b=se['clubs']
        wa,wb=t[a][0],t[b][0]
        exp=a if wa>wb else b if wb>wa else None
        tag='' if exp else f'(tie {wa}) seeds {seed.get(a)},{seed.get(b)}'
        if exp and exp!=se['home_court']: print(s,se['id'],'home court',se['home_court'],'better record',exp)
        if not exp: print(s,se['id'],'equal record',a,b,tag,'home',se['home_court'])
        # game home pattern
        hg=[1,2,5,7] if se['round']!='finals' else [1,2,6,7]
        for g in se['games']:
            want=se['home_court'] if g['game'] in hg else (b if se['home_court']==a else a)
            if g['home']!=want: print(s,se['id'],'game',g['game'],'home',g['home'],'expected',want)
        # later-round pairing from bracket
    # bracket advancement
    rounds={}
    for se in pj['series']: rounds.setdefault(se['round'],[]).append(se)
    winners={se['winner'] for se in rounds['first_round']}
    for se in rounds['conference_semifinals']:
        if not set(se['clubs'])<=winners: print(s,'semis clubs not first-round winners',se['clubs'])
    w2={se['winner'] for se in rounds['conference_semifinals']}
    for se in rounds['conference_finals']:
        if not set(se['clubs'])<=w2: print(s,'conf finals clubs',se['clubs'])
    w3={se['winner'] for se in rounds['conference_finals']}
    for se in rounds['finals']:
        if set(se['clubs'])!=w3: print(s,'finals clubs',se['clubs'],w3)
    print(s,'ok')
