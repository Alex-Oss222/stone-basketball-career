import re, glob, json, collections, sys
sys.path.insert(0,'/home/user/stone-basketball-career')
from pathlib import Path
from runtime.stat_layout import scope_for
L='/home/user/stone-basketball-career/career/Dwyane_Wade/Stats_and_Awards/League'
reg={p['registry_id']:p for p in json.load(open(L+'/player_registry.json'))['players']}
files=sorted(glob.glob(L+'/**/League_Stats.md', recursive=True))
print(collections.Counter(f.split('League/')[1][:7] for f in files))
print([f.split('League/')[1] for f in files if f.split('League/')[1].startswith('2003-04')][:40])
added=collections.Counter((p.get('added_on') or '')[:7] for p in reg.values())
print(sorted(added.items()))
# players added after 2004-06-30 but by 2006-06-20
print(sum(1 for p in reg.values() if (p.get('added_on') or '')>'2004-06-30'), sum(1 for p in reg.values() if (p.get('added_on') or '')>'2005-06-30'))
# rows by page-end rule
tot=collections.Counter(); pl=collections.defaultdict(set)
for f in files:
    sc=scope_for(Path(f), [], '2006-06-20'); end=min(sc['end'],'2006-06-20')
    season=f.split('League/')[1][:7]
    for m in re.finditer(r'^\| \[[^\]]*\]\((?:\.\./)*Players/([^)]*)\.md\)', open(f).read(), re.M):
        p=reg[m.group(1)]
        if (p.get('added_on') or '')>end: tot[season]+=1; pl[season].add(m.group(1))
print('page-end rule', {s:(tot[s],len(pl[s])) for s in tot})
