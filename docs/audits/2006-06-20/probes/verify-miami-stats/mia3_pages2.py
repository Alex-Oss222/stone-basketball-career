import sys, json, re
from pathlib import Path
R=Path('/home/user/stone-basketball-career'); C=R/'career/Dwyane_Wade'
targets=('Malik Allen','Jerome Beasley','Bernard Robinson','Christian Drejer','Uroš Slokar')
tot={}; nogames={}
for s in ['2003-04','2004-05','2005-06']:
    for pg in sorted((C/'Stats_and_Awards/Team'/s).rglob('Team_Stats.md')):
        t=pg.read_text()
        sec=t.split('## Production')[1].split('\n## ')[0] if '## Production' in t else None
        if sec is None:
            # find production table by header
            pass
        # production table: header starts with | Player | Pos | G | MIN
        lines=t.splitlines()
        hdr=[i for i,l in enumerate(lines) if l.startswith('| Player | Pos | G |')]
        status=re.search(r'^As of [^\n]*$',t,re.M).group(0)
        for i in hdr:
            j=i+2
            while j<len(lines) and lines[j].startswith('|'):
                c=[x.strip() for x in lines[j].strip('|').split('|')]
                if c[0] in targets:
                    key=(s,c[0]); tot.setdefault(key,[]).append(str(pg.relative_to(C/'Stats_and_Awards/Team')))
                    if 'closed Miami game' not in status: nogames.setdefault(key,[]).append(status[:80])
                j+=1
for k,v in tot.items(): print(k,len(v), 'no-game pages', len(nogames.get(k,[])), nogames.get(k,[])[:1])
print('total',sum(len(v) for v in tot.values()))
