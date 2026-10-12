import sys, json, re, collections
sys.path.insert(0,'/home/user/stone-basketball-career')
from pathlib import Path
from runtime.stat_layout import scope_for
from runtime.league_cards import age_on
ROOT=Path('/home/user/stone-basketball-career')
CD=ROOT/'career/Dwyane_Wade/Stats_and_Awards/League/Players'
reg=json.load(open(ROOT/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
byid={p['registry_id']:p for p in reg}
hdr_bad=[]; born_bad=[]; row_bad=collections.defaultdict(list); rows=0; cards=0; html_bad=[]
for md in sorted(CD.glob('*.md')):
    if md.name=='README.md': continue
    cards+=1
    rid=md.stem; p=byid.get(rid)
    t=md.read_text()
    on=re.search(r'\*\*Card date:\*\* (\S+)',t).group(1)
    m=re.search(r'\*\*Born:\*\* (\S+) · \*\*Age on card date:\*\* (\S+)',t)
    born,age=m.group(1),m.group(2)
    if p is None: hdr_bad.append((rid,'not in registry')); continue
    if born!=str(p.get('birth_date')): born_bad.append((rid,born,p.get('birth_date')))
    exp=age_on(p.get('birth_date'),on)
    if str(exp if exp is not None else 'N/A')!=age: hdr_bad.append((rid,age,exp))
    for line in t.splitlines():
        mm=re.match(r'^\| \[([^\]]+)\]\(\.\./([^)]+)/League_Stats\.md\) \| ([^|]+) \|',line)
        if not mm: continue
        rows+=1
        folder=ROOT/'career/Dwyane_Wade/Stats_and_Awards/League'/mm.group(2)/'League_Stats.md'
        sc=scope_for(folder,[],on)
        pon=min(sc['end'],on)
        e=age_on(p.get('birth_date'),pon)
        if str(e)!=mm.group(3).strip(): row_bad[rid].append((mm.group(1),mm.group(3).strip(),e))
    h=(CD/f'{rid}.html').read_text()
    a=re.search(r'"age":("?[^,}]*"?)',h)
    if a and a.group(1).strip('"')!=age: html_bad.append((rid,a.group(1),age))
print('cards',cards,'header bad',hdr_bad[:10],len(hdr_bad)); print('born mismatch',born_bad[:5],len(born_bad)); print('html identity age mismatch',html_bad[:5],len(html_bad))
print('period rows',rows,'bad rows',sum(len(v) for v in row_bad.values()),'players',len(row_bad))
for k,v in list(row_bad.items())[:8]: print(k,len(v),v[:3])
json.dump(row_bad,open('cards_age_bad.json','w'),indent=1)
