"""Wade's contract profile from the catalog builder: the exercised 2006-07 team option is missing."""
import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime.player_contracts import build_contract_catalog
root = Path('/home/user/stone-basketball-career')
cat = build_contract_catalog(root, root / 'career/Dwyane_Wade', '2006-06-20')
profiles = cat['players']
w = None
for k, v in (profiles.items() if isinstance(profiles, dict) else enumerate(profiles)):
    if isinstance(v, dict) and v.get('name') == 'Dwyane Wade':
        w = v; break
cur = w.get('current') or {}
print('options:', cur.get('options'))
print('amount kinds:', [(r['season'], r['amount_kind']) for r in cur.get('salary_rows', [])])
dec = [d for d in json.load(open(root / 'career/Dwyane_Wade/2005-06/League/option_decisions.json'))['decisions'] if d.get('bbr_id') == 'wadedw01']
print('option decision record:', [(d['option_season'], d['kind'], d['decision'], d['applied']) for d in dec])
# rows in Miami's 2005-06 schedule whose option was exercised and then disappeared from amount_kind
rows = json.load(open(root / 'career/Dwyane_Wade/2005-06/00_Team/Finances/contract_schedules.json'))['players']
print('Miami rows with option_history:', [(r['player'], r.get('option_history'), r.get('amount_kind')) for r in rows if r.get('option_history')])
