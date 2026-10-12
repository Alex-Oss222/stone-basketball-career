import re, sys, glob, collections
sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime.league_cards import age_on
ROOT='/home/user/stone-basketball-career'
B='1984-01-17'
bad=collections.Counter(); ex=[]; n=0; hdr=0; hbad=[]
for f in glob.glob(f'{ROOT}/career/Dwyane_Wade/**/*.md',recursive=True):
    if '/Stats_and_Awards/League/' in f or '/Stats_and_Awards/Team/' in f or '/00_Team/' in f: continue
    t=open(f).read()
    # per-game table rows: label | Age | Team | Lg
    for m in re.finditer(r'^\| \[?(\d{4}-\d{2}-\d{2})[^|]*\| (\d+) \| [^|]+ \| (NBA|FIBA) \|',t,re.M):
        n+=1
        if str(age_on(B,m.group(1)))!=m.group(2): bad[f]+=1; ex.append((f.replace(ROOT+'/',''),m.group(1),m.group(2)))
    for m in re.finditer(r'Identity as of (\d{4}-\d{2}-\d{2})',t):
        hdr+=1
        a=re.search(r'\| Dwyane Tyrone Wade Jr\. \| (\d+) \|',t)
        if a and str(age_on(B,m.group(1)))!=a.group(1): hbad.append((f.replace(ROOT+'/',''),m.group(1),a.group(1)))
print('dated rows',n,'bad',sum(bad.values()),ex[:5]); print('identity headers',hdr,'bad',len(hbad),hbad[:5])
