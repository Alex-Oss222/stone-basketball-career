import json, re, glob, collections
R='/home/user/stone-basketball-career'
reg=json.load(open(R+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
added={p['registry_id']:p.get('added_on') for p in reg}
coh=collections.Counter((p.get('added_on') or '')[:7] for p in reg if p.get('added_on'))
print(sorted(coh.items()))
tot=collections.Counter(); pages=collections.Counter(); ex={}
for f in glob.glob(R+'/career/Dwyane_Wade/Stats_and_Awards/League/20*/**/League_Stats.md',recursive=True):
    season=re.search(r'/League/(\d{4}-\d{2})/',f).group(1)
    end=f'{int(season[:4])+1}-06-30'; start=f'{season[:4]}-07-01'
    t=open(f).read()
    for m in re.finditer(r'^\| \[([^\]]+)\]\(\.\./[^)]*?Players/([^)]+)\.md\) \| (\S+) \| (\S+) \| NBA \| \S+ \| (\S+) \|',t,re.M):
        rid=m.group(2); a=added.get(rid)
        if a and a>end:
            tot[season]+=1; pages[f]+=1
            ex.setdefault(season,[]).append((m.group(1),a,m.group(4),m.group(5)))
print(tot, len(pages))
for s,v in ex.items(): print(s, v[:6], len({x[0] for x in v}))
