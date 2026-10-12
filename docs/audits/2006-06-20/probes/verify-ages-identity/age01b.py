import sys, json, re, glob, os, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime import league_cards as lc
R='/home/user/stone-basketball-career'
L=R+'/career/Dwyane_Wade/Stats_and_Awards/League'
# read ages from League pages: player link -> age
page_age={}
def ages_of(folder):
    if folder in page_age: return page_age[folder]
    d={}
    p=L+'/'+folder+'/League_Stats.md'
    for line in open(p):
        m=re.match(r'^\| \[[^\]]*\]\((?:\.\./)*Players/([^)]*)\.md\) \| ([^|]*) \|', line)
        if m: d[m.group(1)]=m.group(2).strip()
    page_age[folder]=d; return d
link=re.compile(r'^\| \[[^\]]*\]\(\.\./([^)]*)/League_Stats\.md\) \| ([^|]*) \|')
tot=bad=0; cards=set(); bykind=collections.Counter(); byseason=collections.Counter(); ex={}
for f in sorted(glob.glob(L+'/Players/*.md')):
    pid=os.path.basename(f)[:-3]
    if pid=='README': continue
    for line in open(f):
        m=link.match(line)
        if not m: continue
        folder, age=m.group(1), m.group(2).strip()
        pa=ages_of(folder).get(pid)
        if pa is None: continue
        tot+=1
        if pa!=age:
            bad+=1; cards.add(pid); k=folder.count('/'); bykind[k]+=1; byseason[folder[:7]]+=1
            ex.setdefault(pid,[]).append((folder,age,pa))
print('rows compared',tot,'differ from linked page',bad,'cards',len(cards))
print('by depth (0=season,1=month,2=week)',bykind, byseason)
for p in ('wadedw01','abdursh01','jefferal01','boshch01'):
    print(p, ex.get(p,[])[:3], len(ex.get(p,[])))
# any diff not exactly one year?
odd=[(p,x) for p,l in ex.items() for x in l if not (x[1].isdigit() and x[2].isdigit() and int(x[1])-int(x[2])==1)]
print('non-one-year diffs',len(odd),odd[:5])
