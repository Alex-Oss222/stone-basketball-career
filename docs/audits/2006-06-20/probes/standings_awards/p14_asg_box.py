import json, re
R='/home/user/stone-basketball-career'
def gs(p):
    return (p["pts"] + 0.4*p["fgm"] - 0.7*p["fga"] - 0.4*(p["fta"]-p["ftm"]) + 0.7*p["orb"] + 0.3*p["drb"] + p["stl"] + 0.7*p["ast"] + 0.7*p["blk"] - 0.4*p["pf"] - p["tov"])
for s in ['2003-04','2004-05','2005-06']:
    d=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/all_star_games.json'))
    page=open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/All_Star_Games.md').read()
    for k,g in d['games'].items():
        r=json.load(open(f"{R}/{g['result']}"))
        for side in('home','away'):
            ps=r['player_stats'][side]; ts=r['team_stats'][side]
            for f in ('pts','ast','stl','blk','tov','pf','fgm','fga','tpm','tpa','ftm','fta','orb','drb'):
                sm=sum(p[f] for p in ps)
                if sm!=ts[f]: print(s,k,side,f,'players',sm,'team',ts[f])
            if ts['pts']!=r['final_score'][side]: print(s,k,'score mismatch',side)
            # pts = 2fgm+tpm+ftm
            for p in ps:
                if p['pts']!=2*p['fgm']+p['tpm']+p['ftm']: print(s,k,p['player_id'],'pts formula')
            # selection roster vs box
            team=r[side]
            sel={x['player'] for x in g['teams'][team]['players']}
            box={p['player_id'] for p in ps}
            if sel-box or box-sel: print(s,k,team,'roster vs box',sel-box,box-sel)
        # MVP
        for t in g['mvp']['tally']:
            side='home' if t['team']==r['home'] else 'away'
            p=[p for p in r['player_stats'][side] if p['player_id']==t['player']][0]
            exp=dict(pts=p['pts'],reb=p['orb']+p['drb'],ast=p['ast'],game_score=round(gs(p),1),minutes=round(p['minutes'],1))
            diff={a:(t[a],b) for a,b in exp.items() if t[a]!=b}
            if diff: print(s,k,'mvp tally diff',t['player'],diff)
            won=r['final_score'][side]>r['final_score']['away' if side=='home' else 'home']
            if t['won']!=won: print(s,k,'mvp won flag', t)
        # score on page
        h,a=r['home'],r['away']
        if f"**{h} {r['final_score']['home']}, {a} {r['final_score']['away']}**" not in page: print(s,k,'score line not on page')
    print(s,'checked',list(d['games']))
