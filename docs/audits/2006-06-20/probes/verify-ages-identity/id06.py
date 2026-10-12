import re, glob, json, collections
L='/home/user/stone-basketball-career/career/Dwyane_Wade/Stats_and_Awards/League'
reg={p['registry_id']:p for p in json.load(open(L+'/player_registry.json'))['players']}
out=collections.Counter(); pl=collections.defaultdict(set); g_nonzero=0; pages=collections.Counter()
for f in sorted(glob.glob(L+'/**/League_Stats.md', recursive=True)):
    season=f.split('League/')[1][:7]
    end=f"{int(season[:4])+1}-06-30"
    for m in re.finditer(r'^\| \[[^\]]*\]\((?:\.\./)*Players/([^)]*)\.md\) \| [^|]* \| ([^|]*) \| [^|]* \| [^|]* \| ([^|]*) \|', open(f).read(), re.M):
        pid=m.group(1); p=reg[pid]
        if (p.get('added_on') or '')>end:
            out[season]+=1; pl[season].add(pid); pages[(season,f)]+=1
            if m.group(3).strip()!='0': g_nonzero+=1
for s in out: print(s, 'rows',out[s],'players',len(pl[s]), 'pages', len([k for k in pages if k[0]==s]))
print('nonzero G among them', g_nonzero)
# how many of those have an NBA club label (not N/A / FA)
