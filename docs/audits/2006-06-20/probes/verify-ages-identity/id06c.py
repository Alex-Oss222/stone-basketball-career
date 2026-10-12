import re, glob, json, collections
L='/home/user/stone-basketball-career/career/Dwyane_Wade/Stats_and_Awards/League'
reg={p['registry_id']:p for p in json.load(open(L+'/player_registry.json'))['players']}
for season,end in (('2003-04','2004-06-30'),('2004-05','2005-06-30')):
    f=L+f'/{season}/League_Stats.md'
    cells=collections.Counter(); 
    for m in re.finditer(r'^\| \[[^\]]*\]\((?:\.\./)*Players/([^)]*)\.md\) \| ([^|]*) \| ([^|]*) \|', open(f).read(), re.M):
        p=reg[m.group(1)]
        if (p.get('added_on') or '')>end: cells[m.group(3).strip()]+=1
    print(season, sum(cells.values()), cells.most_common(40))
