import json, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/standings_awards')
import io,contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from p01_standings import results
res=results('2005-06')
west=['Dallas Mavericks','Phoenix Suns','San Antonio Spurs','Sacramento Kings','Minnesota Timberwolves','Los Angeles Lakers','New Orleans/Oklahoma City Hornets','Utah Jazz']
east=['Toronto Raptors','Detroit Pistons','Miami Heat','Boston Celtics','Atlanta Hawks','Orlando Magic','New Jersey Nets','Cleveland Cavaliers','Philadelphia 76ers']
def rec(c,ag):
    w=l=0;diff=0
    for d in res.values():
        if c not in(d['home'],d['away']):continue
        o=d['away'] if c==d['home'] else d['home']
        if ag is not None and o not in ag:continue
        hw=d['final_score']['home']>d['final_score']['away']
        won=(hw and c==d['home']) or (not hw and c==d['away'])
        w+=won;l+=not won
        diff+=(d['final_score']['home']-d['final_score']['away'])*(1 if c==d['home'] else -1)
    return w,l,diff
for c in ['Phoenix Suns','Dallas Mavericks']:
    print(c,'own-conf playoff',rec(c,set(west)-{c}),'other-conf playoff (East top8 + tie)',rec(c,set(east)),'all',rec(c,None))
