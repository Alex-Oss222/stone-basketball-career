import re
from pathlib import Path
C=Path('/home/user/stone-basketball-career/career/Dwyane_Wade')
flag=[]; mixed=[]
for s in ['2003-04','2004-05','2005-06']:
    for card in sorted((C/s/'00_Team/Team/Player_Cards').glob('*.md')):
        if card.name in ('TEMPLATE.md','README.md'): continue
        t=card.read_text()
        if '## Regular-season statistics by year' not in t: continue
        sec=t.split('## Regular-season statistics by year')[1].split('\n## ')[0]
        m=re.search(r'^\*\*Coverage:\*\* ([^\n]*)$',sec,re.M)
        cov=m.group(1) if m else ''
        rows={}
        for line in sec.splitlines():
            if re.match(r'^\| 20\d\d-\d\d \|',line):
                c=[x.strip() for x in line.strip('|').split('|')]
                rows[c[0]]=c
        for season in re.findall(r'(20\d\d-\d\d) (?:has )?not started',cov):
            r=rows.get(season)
            if r and r[2].isdigit() and int(r[2])>0:
                flag.append((str(card.relative_to(C)),season,r[2],cov[:90]))
        # mixed pct formats in FG% column
        fmts=set()
        for r in rows.values():
            if len(r)>11 and r[11] not in ('N/A',''):
                fmts.add('pct' if r[11].endswith('%') else 'dec')
        if len(fmts)>1: mixed.append(str(card.relative_to(C)))
for f in flag: print(f)
print('flagged', len(flag), 'cards', len({f[0] for f in flag}))
print('mixed formats', len(mixed), mixed[:5])
