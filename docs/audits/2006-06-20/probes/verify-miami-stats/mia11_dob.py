import json, re
from pathlib import Path
from datetime import date
R=Path('/home/user/stone-basketball-career'); C=R/'career/Dwyane_Wade'
reg={p.get('bbr_id'):p for p in json.load(open(C/'Stats_and_Awards/League/player_registry.json'))['players'] if p.get('bbr_id')}
regn={p['name']:p for p in json.load(open(C/'Stats_and_Awards/League/player_registry.json'))['players']}
for s in ['2003-04','2004-05','2005-06']:
    for p in json.load(open(C/s/'00_Team/Team/Roster/roster.json'))['players']:
        if not p.get('date_of_birth'):
            r=reg.get(p.get('bbr_id')) or regn.get(p['name'])
            card=C/s/'00_Team/Team/Player_Cards'/Path(p.get('player_card','x')).name
            line=''
            if card.is_file():
                m=re.search(r'Age at assessment:\*\*? ?([^\n·|]*)', card.read_text()); line=m.group(0)[:60] if m else ''
                m2=re.search(r'Assessment date[^\n]*', card.read_text()); ad=m2.group(0)[:60] if m2 else ''
            print(s, p['name'], p.get('status'), 'registry dob', r.get('birth_date') if r else None, '|', line, '|', ad)
