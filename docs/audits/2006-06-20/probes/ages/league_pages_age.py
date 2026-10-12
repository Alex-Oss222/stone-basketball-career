import sys, json, re, collections
sys.path.insert(0,'/home/user/stone-basketball-career')
from pathlib import Path
from runtime.stat_layout import scope_for
from runtime.league_cards import age_on
ROOT=Path('/home/user/stone-basketball-career')
NOW='2006-06-20'
reg=json.load(open(ROOT/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
namecount=collections.Counter(p['name'] for p in reg)
print('duplicate registry names:',[n for n,c in namecount.items() if c>1])
byid={p['registry_id']:p for p in reg}
byname={p['name']:p for p in reg}
bad=collections.defaultdict(list); pages=0; rows=0; na=collections.Counter()
for page in sorted((ROOT/'career/Dwyane_Wade/Stats_and_Awards/League').rglob('*.md')):
    t=page.read_text()
    if '| Player | Age |' not in t: continue
    pages+=1
    rel=page.relative_to(ROOT)
    sc=scope_for(page.relative_to(ROOT) if False else page,[],NOW)
    on=min(sc['end'] or NOW, NOW)
    for line in t.splitlines():
        m=re.match(r'^\| \[([^\]]+)\]\(([^)]+)\) \| ([^|]+) \|',line)
        if not m: continue
        rows+=1
        name, href, age = m.group(1), m.group(2), m.group(3).strip()
        rid=Path(href).stem
        p=byid.get(rid) or byname.get(name)
        if not p: bad[str(rel)].append((name,'not in registry',age)); continue
        exp=age_on(p.get('birth_date'),on)
        if exp is None:
            na[age]+=1
            if age!='N/A': bad[str(rel)].append((name,age,'no birth'));
            continue
        if age!=str(exp):
            bad[str(rel)].append((name,age,exp,p.get('birth_date'),on))
print('pages',pages,'rows',rows,'no-birth ages',na)
tot=sum(len(v) for v in bad.values())
print('bad rows',tot,'pages with bad',len(bad))
for k,v in list(bad.items())[:40]:
    print(k,len(v),v[:4])
json.dump(bad,open('league_pages_age_bad.json','w'),indent=1)
