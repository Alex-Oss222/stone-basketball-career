import sys, json, re, os
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career'); os.chdir(ROOT)
from runtime import jerseys, continuity
from runtime.club_truth import holder
reg = json.load(open('career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
CARDS = ROOT/'career/Dwyane_Wade/Stats_and_Awards/League/Players'
diff=[p for p in reg if p.get('bbr_id') and p['registry_id']!=p['bbr_id']]
print('registry_id != bbr_id:', len(diff), 'no bbr', sum(1 for p in reg if not p.get('bbr_id')))
unassigned=[]; has=[]
for p in diff:
    t=(CARDS/f"{p['registry_id']}.md").read_text()
    j=re.search(r'\*\*Jersey:\*\* ([^·]+)', t).group(1).strip()
    club=re.search(r'\*\*Club on this date:\*\* ([^·]+)', t).group(1).strip()
    if club in ('Free agent',) or '(draft rights)' in club:
        clubname=None if club=='Free agent' else club.replace(' (draft rights)','')
    else: clubname=club
    n_bbr = jerseys.number_for(p['bbr_id'], clubname, ROOT) if clubname else None
    n_reg = jerseys.number_for(p['registry_id'], clubname, ROOT) if clubname else None
    if j=='Unassigned' and n_bbr: unassigned.append((p['registry_id'],p['bbr_id'],clubname,n_bbr,n_reg))
    elif clubname: has.append((p['registry_id'], j, n_bbr))
print('cards Unassigned where bbr lookup gives number:', len(unassigned))
for u in unassigned[:12]: print(' ',u)
print('with club but not in that list:', len(has), has[:5])
print('miami_numbers:', jerseys.miami_numbers(ROOT))
print('wade_number:', jerseys.wade_number(ROOT))
print('butler cands:', jerseys.candidates('butleca01','Miami Heat',ROOT))
for pid in ('wadedw01','butleca01'):
    t=(CARDS/f'{pid}.md').read_text(); print(pid, re.search(r'\*\*Jersey:\*\* ([^·]+)', t).group(1))
