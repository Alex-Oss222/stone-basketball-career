import sys, json, re, os
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career'); os.chdir(ROOT)
from runtime.league_cards import age_on
from runtime.stat_layout import scope_for
from collections import Counter
reg = json.load(open('career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
CARDS = ROOT/'career/Dwyane_Wade/Stats_and_Awards/League/Players'
rowre = re.compile(r'^\| \[([^\]]+)\]\((\.\./2005-06/[^)]*League_Stats\.md)\) \| ([^|]*) \|')
NOW='2006-06-20'
cnt=Counter(); cards=set(); pagecheck=Counter(); ex=[]
page_age_cache={}
def page_age(page, name):
    if page not in page_age_cache:
        t=page.read_text(); d={}
        for m in re.finditer(r'^\| \[([^\]]+)\]\([^)]*\) \| ([^|]*) \|', t, re.M): d[m.group(1)]=m.group(2).strip()
        page_age_cache[page]=d
    return page_age_cache[page].get(name)
for p in reg:
    pid=p['registry_id']; text=(CARDS/f'{pid}.md').read_text()
    for line in text.splitlines():
        m=rowre.match(line)
        if not m: continue
        label, rel, age = m.groups(); age=age.strip()
        page=(CARDS/rel).resolve()
        sc=scope_for(page, [], NOW)
        exp=age_on(p.get('birth_date'), min(sc['end'], NOW))
        kind='week' if 'Week_' in rel else ('month' if rel.count('/')==3 else 'season')
        if exp is not None and str(exp)!=age:
            cnt[kind]+=1; cards.add(pid)
            pa=page_age(page, p['name'])
            pagecheck['page_equals_expected' if pa==str(exp) else f'page_other']+=1
            if pid=='millean02' and len(ex)<3: ex.append((label,age,exp,pa))
print(cnt, sum(cnt.values()), len(cards)); print(pagecheck); print(ex)
