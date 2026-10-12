import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
R=Path('/home/user/stone-basketball-career')
from runtime import team_status
from runtime.miami_cards import injured_on
reg = team_status.register(R, '2006-06-20', '2005-06')
from collections import Counter
print(Counter(p['status'] for p,a,r in reg))
signed=[x for x in reg if x[0].get('status')!='free_agent_rights_held']
print('signed', len(signed), 'injured', sum(1 for x in signed if x[1].startswith('Injured')))
contract=[x for x in signed if x[0]['status']!='unsigned_draft_rights']
print('true under contract', len(contract), 'active', sum(1 for x in contract if not x[1].startswith('Injured')))
for p,a,r in reg: print(p['name'], p['status'], a, r)
