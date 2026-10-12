import sys, json, re, glob
sys.path.insert(0,'/home/user/stone-basketball-career')
from pathlib import Path
from datetime import datetime
from runtime.league_cards import age_on
ROOT=Path('/home/user/stone-basketball-career')
reg=json.load(open(ROOT/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
byname={p['name']:p for p in reg}; bybbr={p['bbr_id']:p for p in reg if p.get('bbr_id')}
bad=[]; n=0
for season in ('2003-04','2004-05','2005-06'):
    roster=json.load(open(ROOT/f'career/Dwyane_Wade/{season}/00_Team/Team/Roster/roster.json'))['players']
    rb={p['name']:p for p in roster}
    for card in sorted((ROOT/f'career/Dwyane_Wade/{season}/00_Team/Team/Player_Cards').glob('*.md')):
        if card.name in ('TEMPLATE.md','README.md'): continue
        t=card.read_text(); n+=1
        name=re.search(r'^# (.+?) \|',t,re.M).group(1)
        a=re.search(r'\*\*Age at assessment:\*\* (\S+)',t)
        d=re.search(r'\*\*Opening assessment:\*\* ([A-Za-z]+ \d+, \d{4})',t)
        pos=re.search(r'\*\*Position:\*\* ([^\n]+?)\s*$',t,re.M)
        if not a or not d: bad.append((season,card.name,'no age/date',a and a.group(1), d and d.group(1))); continue
        day=datetime.strptime(d.group(1),'%B %d, %Y').date().isoformat()
        r=rb.get(name,{})
        birth=r.get('date_of_birth')
        regp=byname.get(name) or bybbr.get(r.get('bbr_id'))
        rbirth=regp.get('birth_date') if regp else None
        if name=='Dwyane Wade': rbirth='1984-01-17'
        if birth and rbirth and birth!=rbirth: bad.append((season,name,'birth differs roster vs registry',birth,rbirth))
        b=birth or rbirth
        exp=age_on(b,day) if b else None
        if str(exp if exp is not None else 'N/A')!=a.group(1): bad.append((season,name,'age',a.group(1),exp,b,day))
        if regp and pos and name!='Dwyane Wade':
            cardpos=pos.group(1).split(' ')[0]
            if regp['position'] not in pos.group(1).replace(' ','').split('/'): bad.append((season,name,'pos card vs registry',pos.group(1),regp['position'],r.get('positions')))
print('cards',n)
for b in bad: print(b)
