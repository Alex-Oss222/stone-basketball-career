import json, sys, io, contextlib
sys.path.insert(0,'/home/user/stone-basketball-career')
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
R='/home/user/stone-basketball-career'
from runtime import club_truth
from runtime.seasons import conferences as align
GROUP = {"PG": "G", "SG": "G", "G": "G", "SF": "F", "PF": "F", "F": "F", "C": "C"}
reg=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))
reg=reg['players'] if isinstance(reg,dict) else reg
byb={p.get('bbr_id'):p for p in reg}
def gs(p):
    return (p["pts"] + 0.4*p["fgm"] - 0.7*p["fga"] - 0.4*(p["fta"]-p["ftm"]) + 0.7*p["orb"] + 0.3*p["drb"] + p["stl"] + 0.7*p["ast"] + 0.7*p["blk"] - 0.4*p["pf"] - p["tov"])
for s in ['2004-05','2005-06']:
    res=results(s)
    conf={t:c for c,ts in align(s,R).items() for t in ts}
    d=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/all_star.json'))
    from runtime.award_decisions import registry_names
    names=registry_names(R,s); inv={v:k for k,v in names.items()}
    for st in d['steps']:
        groups=[]
        if 'teams' in st: groups=[(k,v) for k,v in st['teams'].items()]
        for c,v in (st.get('conferences') or {}).items():
            if isinstance(v,dict):
                for k,ps in v.items():
                    if isinstance(ps,list) and ps and isinstance(ps[0],dict) and 'player' in ps[0]: groups.append((c+'/'+k,ps))
        for gname,ps in groups:
            for p in ps:
                if 'games' not in p: continue
                b=p.get('bbr_id'); r=byb.get(b,{})
                pos=GROUP.get(r.get('position'))
                if pos!=p.get('position'): print(s,st['step'],gname,p['player'],'pos shown',p.get('position'),'registry',r.get('position'))
                h=club_truth.holder(b,p['player'],st['announced_on'],R)[0]
                h2=club_truth.holder(b,p['player'],st['evidence_through'],R)[0]
                if h!=p['team'] or h2!=p['team']: print(s,st['step'],gname,p['player'],'team',p['team'],'holder@announce',h,'holder@evidence',h2)
                if st['step']!='rookie_challenge' and conf.get(p['team'])!=gname.split('/')[0]: print(s,st['step'],'conference mismatch',p['player'],p['team'],gname)
                # stats
                nm=inv.get(p['player'],p['player'])
                L=[];tg=None
                for rr in res.values():
                    if rr['game_date']>st['evidence_through']: continue
                    for side in('home','away'):
                        for q in rr['player_stats'][side]:
                            if q['player_id'] in (nm,p['player']) and q['minutes']>0: L.append((rr['game_date'],rr[side],q))
                if not L: print(s,st['step'],p['player'],'no games'); continue
                g=len(L)
                exp=dict(games=g,pts=round(sum(q['pts'] for _,_,q in L)/g,1),reb=round(sum(q['orb']+q['drb'] for _,_,q in L)/g,1),ast=round(sum(q['ast'] for _,_,q in L)/g,1),game_score=round(sum(gs(q) for _,_,q in L)/g,2))
                diff={k:(p[k],v) for k,v in exp.items() if p.get(k)!=v}
                if diff: print(s,st['step'],p['player'],'stat diff',diff)
                last=sorted(L,key=lambda x:x[0])[-1][1]
                if last!=p['team']: print(s,st['step'],p['player'],'last game team',last,'shown',p['team'])
    for a in d['all_stars']:
        h=club_truth.holder(a['bbr_id'],a['player'],a['selected_on'],R)[0]
        if h!=a['team']: print(s,'all_stars',a['player'],a['team'],'holder',h)
        if conf.get(a['team'])!=a['conference']: print(s,'all_stars conf',a)
