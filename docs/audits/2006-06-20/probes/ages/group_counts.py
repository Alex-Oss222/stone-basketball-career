import re,collections
from pathlib import Path
ROOT=Path('/home/user/stone-basketball-career')
mis=collections.Counter(); ex=[]
for page in sorted((ROOT/'career/Dwyane_Wade/Stats_and_Awards/League').rglob('League_Stats.md')):
    t=page.read_text()
    head=re.search(r'^(\d+) tracked players',t,re.M)
    total=0
    for m in re.finditer(r'<summary>(\w+) · [^·]+ · (\d+) players</summary>(.*?)</details>',t,re.S):
        n=sum(1 for l in m.group(3).splitlines() if l.startswith('| ['))
        total+=n
        if n!=int(m.group(2)): mis[str(page.relative_to(ROOT))]+=1; ex.append((str(page.relative_to(ROOT)),m.group(1),m.group(2),n))
    if head and int(head.group(1))!=total: ex.append((str(page.relative_to(ROOT)),'HEAD',head.group(1),total))
print(len(mis), len(ex)); print(ex[:12])
