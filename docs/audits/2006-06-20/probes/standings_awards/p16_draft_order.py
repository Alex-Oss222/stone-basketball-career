import json, sys, io, contextlib
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import table
R='/home/user/stone-basketball-career'
for s,f in [('2004-05','career/Dwyane_Wade/2004-05/09_Draft/draft_order_2005.json'),('2005-06','career/Dwyane_Wade/2005-06/09_Draft/draft_order_2006.json')]:
    t,_=table(s)
    d=json.load(open(f'{R}/{f}'))
    seeds=[x['club'] for x in d['lottery_seeds']]
    pj=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/playoffs.json'))
    playoff={r['club'] for rows in pj['seeds'].values() for r in rows}
    nonp=set(t)-playoff
    if set(seeds)!=nonp: print(s,'lottery set mismatch',set(seeds)^nonp)
    for x in d['lottery_seeds']:
        w,l=t[x['club']]
        if x['record']!=f'{w}-{l}': print(s,'seed record',x)
    pcts=[t[c][0]/82 for c in seeds]
    if pcts!=sorted(pcts): print(s,'seeds not worst first')
    # first round non-lottery order
    code={}
    for p in d['picks']: pass
    r1=[p for p in d['picks'] if p['round']==1]
    r2=[p for p in d['picks'] if p['round']==2]
    print(s,'r1',len(r1),'r2',len(r2))
    # map original code -> club via owner_club when owner==original
    c2n={}
    for p in d['picks']:
        if p['owner']==p['original']: c2n[p['original']]=p['owner_club']
    c2n.setdefault('PHI','Philadelphia 76ers')
    miss=[p['original'] for p in d['picks'] if p['original'] not in c2n]
    if miss: print(' unmapped codes',set(miss))
    rec=lambda code:t[c2n[code]][0] if code in c2n else None
    w1=[rec(p['original']) for p in r1[14:]]
    if w1!=sorted(w1): print(s,'playoff part of r1 not worst-first',w1)
    w2=[rec(p['original']) for p in r2]
    if [x for x in w2 if x is not None]!=sorted(x for x in w2 if x is not None): print(s,'r2 not reverse record',w2)
    # lottery-pick: winners then seed order, max fall 3
    rest=[c for c in seeds if c not in d['lottery_winners']]
    exp=d['lottery_winners']+rest
    got=[c2n.get(p['original']) for p in r1[:14]]
    if got!=exp: print(s,'lottery picks order',got,exp)
