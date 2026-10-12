import sys, json, re
from pathlib import Path
R=Path('/home/user/stone-basketball-career'); C=R/'career/Dwyane_Wade'
targets=('Malik Allen','Jerome Beasley','Bernard Robinson','Christian Drejer','Uroš Slokar')
tot={}
for s in ['2003-04','2004-05','2005-06']:
    pages=sorted((C/'Stats_and_Awards/Team'/s).rglob('Team_Stats.md'))
    print(s,'pages',len(pages))
    for pg in pages:
        t=pg.read_text()
        status=re.search(r'^As of [^\n]*$',t,re.M).group(0)
        for name in targets:
            rows=[l for l in t.splitlines() if l.startswith(f'| {name} |')]
            if rows:
                tot.setdefault((s,name),[]).append((str(pg.relative_to(C/'Stats_and_Awards/Team')), rows[0][:60], status[:70]))
for k,v in tot.items():
    print(k, len(v))
    for x in v[:2]: print('   ',x)
print('total', sum(len(v) for v in tot.values()))
