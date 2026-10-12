"""Miami's 2005-06 register on 2006-06-20 and the 2004-05 register contract lines (read-only)."""
import json, re
from pathlib import Path
C = Path('/home/user/stone-basketball-career/career/Dwyane_Wade')
reg = json.loads((C / '2005-06/00_Team/Team/Roster/roster.json').read_text())['players']
cs = {p['player']: p for p in json.loads((C / '2005-06/00_Team/Finances/contract_schedules.json').read_text())['players']}
il = json.loads((C / '2005-06/00_Team/Transactions/injured_list.json').read_text())['entries']
GONE = ("released", "traded", "signed_elsewhere", "voided", "waived", "renounced", "declined")
active = [p for p in reg if not any(w in p['status'] for w in GONE)]
signed = [p for p in active if p['status'] not in ('free_agent_rights_held', 'unsigned_draft_rights')]
on_il = {e['player'] for e in il if e['placed'] <= '2006-06-20' and (e['activated'] is None or e['activated'] > '2006-06-20')}
print('register not gone', len(active), '| under contract', len(signed), '| on IL', len(on_il & {p['name'] for p in signed}), '| active', len(signed) - len(on_il & {p['name'] for p in signed}))
print('rights only:', [p['name'] for p in active if p not in signed])
print('contracts ending with 2005-06 (no 2006-07 salary):', [p['name'] for p in signed if not cs.get(p['name'], {}).get('schedule', {}).get('2006-07')])
print('their register status:', {p['name']: p['status'] for p in signed if not cs.get(p['name'], {}).get('schedule', {}).get('2006-07')})
print('free_agent_rights.json players:', json.loads((C / '2005-06/00_Team/Finances/free_agent_rights.json').read_text())['players'])
print()
r4 = {p['name']: p for p in json.loads((C / '2004-05/00_Team/Team/Roster/roster.json').read_text())['players']}
cs4 = {p['player']: p for p in json.loads((C / '2004-05/00_Team/Finances/contract_schedules.json').read_text())['players']}
for n in ('Brian Grant', 'Caron Butler'):
    sch = cs4[n]['schedule']; yrs = [k for k in sorted(sch) if k >= '2004-05' and sch[k]]
    print(n, '| register:', r4[n]['control'], '| schedule from 2004-05:', len(yrs), 'seasons', f"${sum(sch[k] for k in yrs):,}")
print()
births = {p['name']: p.get('birth_date') for p in json.loads((C / 'Stats_and_Awards/League/player_registry.json').read_text())['players']}
print('2004-05 register entries without date_of_birth but with a registry birth date:',
      {n: births.get(n) for n, p in r4.items() if not p.get('date_of_birth') and births.get(n)})
