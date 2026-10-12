import sys, json, os, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career'); os.chdir(ROOT)
cat = pickle.load(open('/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/verify-cards-contracts/cat.pkl','rb'))
P={p['id']:p for p in cat['players']}
p=P['brownpj01']
print('current', p['current']['id'])
for h in p['history']:
    print(h['id'], h['team'], h['status'], h['signed_on'], [(r['season'], r['salary']) for r in h['salary_rows']], h['scheduled_subtotal'], [(a['date'],a['from'],a['to']) for a in h['assignment_history']])
# all active Miami sheet rows vs current page schedule
d=json.load(open('career/Dwyane_Wade/2005-06/00_Team/Finances/contract_schedules.json'))
byname={x['name']:x for x in cat['players']}
for row in d['players']:
    if row['status'] not in ('under_contract','under_rookie_contract','under_contract_guarantee_amended'): continue
    pr=byname.get(row['player'])
    if not pr or not pr['current']: print('NO CURRENT', row['player']); continue
    cur={r['season']:r['salary'] for r in pr['current']['salary_rows']}
    bad={s:(v,cur.get(s)) for s,v in row['schedule'].items() if s>='2005-06' and cur.get(s)!=v}
    if bad: print('MISMATCH', row['player'], pr['current']['id'], bad)
