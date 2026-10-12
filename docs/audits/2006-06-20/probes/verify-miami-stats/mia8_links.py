import re
from pathlib import Path
C=Path('/home/user/stone-basketball-career/career/Dwyane_Wade')
pages=list((C/'Stats_and_Awards/Team').rglob('*.md'))
for s in ['2003-04','2004-05','2005-06']:
    pages+= [p for p in (C/s/'00_Team').rglob('*.md')]
broken=[]
for p in pages:
    for m in re.finditer(r'\]\(([^)#\s]+)(?:#[^)]*)?\)', p.read_text()):
        tgt=m.group(1)
        if tgt.startswith('http') or tgt.startswith('mailto'): continue
        if not (p.parent/tgt).exists(): broken.append((str(p.relative_to(C)), tgt))
from collections import Counter
print(len(pages),'pages; broken', len(broken))
for b in sorted(set(broken)): print(b)
