import json, re
R='/home/user/stone-basketball-career'
base=f'{R}/career/Dwyane_Wade/FIBA/Continental_Cups/2005'
page=open(f'{base}/README.md').read()
bad=0
for m in re.finditer(r'^\| (\d+) \| (\d{4}-\d\d-\d\d) \| ([^|]+?) \| ([^|]+?) \| (\d+)-(\d+) \| \[box\]\(Games/([^)]+)\) \|$',page,re.M):
    n,d,h,a,hs,as_,f=m.groups()
    r=json.load(open(f'{base}/Games/{f}'))
    shown_winner=h if int(hs)>int(as_) else a
    true_winner=r['home'] if r['final_score']['home']>r['final_score']['away'] else r['away']
    if shown_winner!=true_winner or {h:int(hs),a:int(as_)}!={r['home']:r['final_score']['home'],r['away']:r['final_score']['away']}:
        bad+=1; print(f'game {n}: page "{h} {hs} - {a} {as_}" (implies {shown_winner} won); result {r["home"]} {r["final_score"]["home"]}, {r["away"]} {r["final_score"]["away"]} ({true_winner} won)')
print('rows wrong',bad)
