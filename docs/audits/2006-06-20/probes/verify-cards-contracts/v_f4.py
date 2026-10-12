import sys, json, os, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career'); os.chdir(ROOT)
cat = pickle.load(open('/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/verify-cards-contracts/cat.pkl','rb'))
P = {p['id']:p for p in cat['players']}
def show(pid):
    p=P[pid]; c=p['current']
    print(pid, '| team', p['team'], '| status', p['status'], '| current', c and (c['id'], c['team'], c['status'], [r['season'] for r in c['salary_rows']], c['expiry_date']))
    for h in p['history']: print('    hist', h['id'], h['team'], h['status'], h['signed_on'], [ (r['season'], r['salary']) for r in h['salary_rows']], [a['date']+':'+str(a['to']) for a in h['assignment_history']])
for pid in ['jonesju01','alstora01','butlera01','brownkw01','ratlith01','foylead01','cassesa01','wellsbo01']:
    if pid in P: show(pid)
    else: print('missing', pid)
from runtime.club_truth import holder
import inspect; print(inspect.signature(holder))
