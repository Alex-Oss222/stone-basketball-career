import sys, json, os, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career'); os.chdir(ROOT)
cat = pickle.load(open('/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/verify-cards-contracts/cat.pkl','rb'))
P={p['id']:p for p in cat['players']}
for pid in ('jonesed02','murrala01'):
    c=P[pid]['current']; print(pid, c['id'], 'team', c['team'])
    for a in c['assignment_history']: print('   ', a['date'], a['from'], '->', a['to'], a['kind'], a['source']['path'] if isinstance(a['source'],dict) else a['source'])
# all contracts whose team != latest assignment's 'to'
mis=[]
for p in cat['players']:
    for h in p['history']:
        ah=h['assignment_history']
        if ah:
            last=max(ah, key=lambda a:a['date'])
            if last['to']!=h['team']: mis.append((p['id'],h['id'],h['team'],last['date'],last['to'], p['current'] and p['current']['id']==h['id']))
print(len(mis)); [print(' ',m) for m in mis]
