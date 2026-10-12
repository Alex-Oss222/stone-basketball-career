import re, glob, json
from datetime import date
R='/home/user/stone-basketball-career'
reg={p['registry_id']:p for p in json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
def age(b,on):
    b=date.fromisoformat(b); on=date.fromisoformat(on); return on.year-b.year-((on.month,on.day)<(b.month,b.day))
pages=sorted(glob.glob(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/20*/**/League_Stats.md',recursive=True))
n=0;wrong=0
for p in pages:
    t=open(p).read(); m=re.search(r'identity cutoff \((\d{4}-\d\d-\d\d)\)',t)
    if not m: continue
    n+=1; cut=m.group(1); bad=0
    for row in re.finditer(r'^\| \[[^\]]+\]\([./]*Players/([^)]+)\.md\) \| (\d+) \|',t,re.M):
        pid,a=row.groups(); b=reg.get(pid,{}).get('birth_date')
        if b and age(b,cut)!=int(a): bad+=1
    if bad: wrong+=1
print('pages with caption',n,'pages where shown ages disagree with the caption date',wrong)
