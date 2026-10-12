import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime.player_contracts import build_contract_catalog
root = Path('/home/user/stone-basketball-career')
cat = build_contract_catalog(root, root/'career/Dwyane_Wade', '2006-06-20')
for p in cat['players']:
    if p['id'] in ('wadedw01', 'butleca01'):
        print('==', p['id'], p['name'], p['team'], p['status'])
        print(' keys', list(p.keys()))
        for c in p['history']:
            print(' ', c['id'], c['status'], 'term', c['original_term_seasons'], 'total', c['reported_total'])
            print('   options:', c['options'])
            for r in c['salary_rows']: print('    ', r['season'], r['salary'], r['amount_kind'])
            print('   record_as_of', c['record_as_of'])
            print('   sources', [s.get('path') or s.get('href') for s in c['sources']][:8])
