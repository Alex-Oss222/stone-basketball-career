import sys, json, os, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career'); os.chdir(ROOT)
cat = pickle.load(open('/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/verify-cards-contracts/cat.pkl','rb'))
from runtime.club_truth import holder
reg = {p['registry_id']:p for p in json.load(open('career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
out=[]; nonmiami=0
for p in cat['players']:
    c=p['current']
    if not c: continue
    seasons=[r['season'] for r in c['salary_rows'] if r['amount_kind']!='prior_season_salary_reference']
    last=max(seasons) if seasons else None
    if last and last < '2005-06':
        if c['team']=='Miami Heat':
            r=reg.get(p['id'],{})
            club,_=holder(r.get('bbr_id'), p['name'], '2006-06-20')
            out.append((p['id'], c['id'], c['status'], seasons, c['end_season'], c['expiry_date'], club, [ (a['date'],a['to']) for a in c['assignment_history']]))
        else: nonmiami+=1
print(len(out)); [print(' ',o) for o in out]
print('non-Miami current with last season < 2005-06:', nonmiami)
# Miami sheets: which seasons list these players
for s in ('2003-04','2004-05','2005-06'):
    d=json.load(open(f'career/Dwyane_Wade/{s}/00_Team/Finances/contract_schedules.json'))
    names={x['player']:(x['status'], x['schedule']) for x in d['players']}
    for pid in [o[0] for o in out]:
        nm=[p['name'] for p in cat['players'] if p['id']==pid][0]
        if nm in names: print(s, nm, names[nm])
