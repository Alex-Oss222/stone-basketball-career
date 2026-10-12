import re, glob, collections
L='/home/user/stone-basketball-career/career/Dwyane_Wade/Stats_and_Awards/League'
bad=0; pages=0; rowcounts=collections.Counter(); tracked=collections.Counter()
for f in glob.glob(L+'/*/**/League_Stats.md', recursive=True)+glob.glob(L+'/*/League_Stats.md'):
    pass
files=sorted(set(glob.glob(L+'/**/League_Stats.md', recursive=True)))
for f in files:
    t=open(f).read(); pages+=1
    m=re.search(r'^(\d+) tracked players', t, re.M)
    total=0
    for g in re.finditer(r'<summary>(\w+) · [^·]* · (\d+) players</summary>\n(.*?)</details>', t, re.S):
        n=len(re.findall(r'^\| \[', g.group(3), re.M))
        total+=n
        if int(g.group(2))!=n: bad+=1
    if m and int(m.group(1))!=total: bad+=1
    tracked[(m.group(1) if m else None, total)]+=1
print('pages',pages,'mismatching labels',bad, tracked)
