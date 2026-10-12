import json, sys, io, contextlib
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
R='/home/user/stone-basketball-career'
def gs(p):
    return (p["pts"] + 0.4*p["fgm"] - 0.7*p["fga"] - 0.4*(p["fta"]-p["ftm"]) + 0.7*p["orb"] + 0.3*p["drb"] + p["stl"] + 0.7*p["ast"] + 0.7*p["blk"] - 0.4*p["pf"] - p["tov"])
careers=json.load(open(f'{R}/library/careers/nba_player_careers.json'))['players']
reg=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))
reg=reg['players'] if isinstance(reg,dict) else reg
n2b={p['name']:p.get('bbr_id') for p in reg}
def lines(s):
    out={}
    for r in results(s).values():
        for side in('home','away'):
            for p in r['player_stats'][side]:
                if p['minutes']>0:
                    t=out.setdefault(p['player_id'],[0,0.0]); t[0]+=1; t[1]+=gs(p)
    return out
prev={'2004-05':'2003-04','2005-06':'2004-05'}
for s in ['2004-05','2005-06']:
    P=lines(prev[s])
    sa=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/season_awards.json'))
    for x in sa['decisions']:
        if x['award']=='mip':
            for t in x['tally']:
                pr=P.get(t['player'])
                print(s,'MIP',t['player'],t['team'],'prior shown',t['prior_game_score'],'recomputed',None if not pr else (pr[0],round(pr[1]/pr[0],2)),'pts',t['points'])
        if x['award'] in('roy','all_rookie'):
            people=list(x.get('tally') or [])
            for tm in x.get('teams') or []: people+=tm['players']
            for p in people:
                b=n2b.get(p['player'])
                first=min((careers.get(b) or {}).get('seasons') or {'?':0}) if b else '?'
                if first!=s: print(s,x['award'],p['player'],'bbr',b,'first season in careers',first)
