import json, sys, glob, re, os
from collections import defaultdict
sys.path.insert(0,'/home/user/stone-basketball-career')
R='/home/user/stone-basketball-career'
import io,contextlib
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
def gs(p):
    return (p["pts"] + 0.4*p["fgm"] - 0.7*p["fga"] - 0.4*(p["fta"]-p["ftm"]) + 0.7*p["orb"] + 0.3*p["drb"] + p["stl"] + 0.7*p["ast"] + 0.7*p["blk"] - 0.4*p["pf"] - p["tov"])
reg=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))
reg=reg['players'] if isinstance(reg,dict) else reg
name2bbr={p['name']:p.get('bbr_id') for p in reg}
from runtime import club_truth
from runtime.seasons import conferences as align
for s in ["2003-04","2004-05"]:
    res=results(s)
    conf={t:c for c,ts in align(s,R).items() for t in ts}
    # per-game bbr ids via frozen request
    from runtime.award_decisions import registry_names
    names=registry_names(R,s)
    dec=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/award_decisions.json'))
    for d in dec['decisions']:
        st,en=d['period_start'],d['period_end']
        lines=defaultdict(list)
        for r in res.values():
            if not st<=r['game_date']<=en: continue
            for side,oth in (('home','away'),('away','home')):
                won=r['final_score'][side]>r['final_score'][oth]
                for p in r['player_stats'][side]:
                    if p['minutes']>0:
                        lines[p['player_id']].append((r['game_date'],r[side],won,gs(p),p['pts'],p['orb']+p['drb'],p['ast']))
        for x in d['shortlist']:
            nm=x['player']
            L=lines.get(nm)
            if L is None:
                # registry name alias
                cands=[k for k in lines if name2bbr.get(k) and name2bbr.get(k)==name2bbr.get(nm)]
                L=lines.get(cands[0]) if cands else None
            if not L:
                inv={v:k for k,v in names.items()}
                L=lines.get(inv.get(nm))
            if not L: print(s,d["id"],"no lines for",nm); continue
            n=len(L); w=sum(g[2] for g in L)
            exp=dict(games=n,wins=w,losses=n-w,pts=round(sum(g[4] for g in L)/n,1),reb=round(sum(g[5] for g in L)/n,1),ast=round(sum(g[6] for g in L)/n,1),game_score=round(sum(g[3] for g in L)/n,2))
            diff={k:(x[k],v) for k,v in exp.items() if x[k]!=v}
            last=sorted(L)[-1][1]
            teams={g[1] for g in L}
            if diff: print(s,d['id'],nm,'DIFF',diff)
            if last!=x['team']: print(s,d['id'],nm,'last game team',last,'listed',x['team'])
            if len(teams)>1: print(s,d['id'],nm,'multiple teams in window',teams)
            if False:
                bbr=name2bbr.get(nm)
                h=club_truth.holder(bbr,nm,en,R)[0]
                if h!=x['team']: print(s,d['id'],nm,'holder on',en,'=',h,'listed',x['team'],'conf',conf.get(h),'vs',d['conference'])
            if conf.get(x['team'])!=d['conference']: print(s,d['id'],nm,'team conf mismatch',x['team'])
