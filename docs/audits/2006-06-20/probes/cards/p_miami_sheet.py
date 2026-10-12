import sys, json, pickle
ROOT='/home/user/stone-basketball-career'
c = pickle.load(open('catalog_full.pkl','rb'))
byname = {p['name']: p for p in c['players']}
sheet = json.load(open(ROOT+'/career/Dwyane_Wade/2005-06/00_Team/Finances/contract_schedules.json'))
for row in sheet['players']:
    p = byname.get(row['player'])
    if not p: print('NO PROFILE', row['player']); continue
    cur = p.get('current')
    sched = {k: v for k, v in (row.get('schedule') or {}).items()}
    if cur:
        page = {r['season']: r['salary'] for r in cur['salary_rows'] if r['amount_kind'] != 'prior_season_salary_reference'}
        kinds = {r['season']: r['amount_kind'] for r in cur['salary_rows']}
    else:
        page = None; kinds = None
    ok = page == sched
    print(('OK ' if ok else 'DIFF'), row['player'], '| sheet', row.get('status'), sched, '| page', p['status'], p['team'], (cur or {}).get('id'), page if not ok else '', (cur or {}).get('team'))
