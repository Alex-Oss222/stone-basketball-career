import sys, json, re
from pathlib import Path
R = Path('/home/user/stone-basketball-career'); C = R/'career/Dwyane_Wade'
sums = {tuple(k.split('|')):v for k,v in json.load(open('mia1_sums.json')).items()}
seasons=['2003-04','2004-05','2005-06']
badcards=set(); zero_rows=0; missing=0; pairs=set()
for folder in seasons:
    for card in sorted((C/folder/'00_Team/Team/Player_Cards').glob('*.md')):
        if card.name=='TEMPLATE.md': continue
        t=card.read_text()
        m=re.search(r'^# (.+)$', t, re.M)
        name=None
        mm=re.search(r'\*\*Name:\*\* ([^\n·|]+)', t) 
        # find player name by matching sums keys
        if '## Playoff statistics by year' not in t:
            print('NO PLAYOFF SECTION', card); continue
        sec=t.split('## Playoff statistics by year')[1].split('\n## ')[0]
        rows={}
        for line in sec.splitlines():
            if line.startswith('| 20'):
                c=[x.strip() for x in line.strip('|').split('|')]
                rows[c[0]]=c
        # determine player name from title
        title=t.splitlines()[0].lstrip('# ').strip()
        # each season up to folder
        for s in seasons[:seasons.index(folder)+1]:
            cand=[k for k in sums if k[0]==s and k[1].lower().replace('.','').replace(' ','_')[:12] in card.stem.replace('.','')[:12+0] ]
            cand=[k for k in sums if k[0]==s and k[1].lower().replace('.','').replace(' ','_')==card.stem]
            if not cand: continue
            v=sums[cand[0]]
            r=rows.get(s)
            if r is None:
                missing+=1; badcards.add(str(card.relative_to(C))); pairs.add((folder,cand[0])); print('MISSING', card.relative_to(C), s, v['g'])
            elif r[2]!=str(v['g']):
                zero_rows+=1; badcards.add(str(card.relative_to(C))); pairs.add((folder,cand[0])); print('WRONG', card.relative_to(C), s, 'shown', r[2], 'expected', v['g'])
print('cards',len(badcards),'wrong rows',zero_rows,'missing rows',missing,'pairs', len(pairs))
