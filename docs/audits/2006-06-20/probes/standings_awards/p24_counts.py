import re, glob, json
R='/home/user/stone-basketball-career'
reg=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
from collections import Counter
print('registry by position',Counter(p.get('position') for p in reg))
pages=sorted(glob.glob(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/20*/**/League_Stats.md',recursive=True))
bad=0
for p in pages:
    t=open(p).read()
    hdr=re.search(r'(\d+) tracked players',t)
    secs=re.findall(r'<summary>(\w+) · [^·]+· (\d+) players</summary>(.*?)</details>',t,re.S)
    rows=0; mism=[]
    for pos,n,body in secs:
        k=len(re.findall(r'^\| \[',body,re.M)); rows+=k
        if k!=int(n): mism.append((pos,int(n),k))
    if mism or (hdr and int(hdr.group(1))!=rows):
        bad+=1
        if bad<=3: print(p.replace(R,''),'header',hdr.group(1) if hdr else None,'rows',rows,'sections (shown,actual)',mism)
print('pages',len(pages),'with count mismatch',bad)
