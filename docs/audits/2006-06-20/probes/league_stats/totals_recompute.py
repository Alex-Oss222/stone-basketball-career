"""Recompute season_evidence.compute_totals in memory (no write) and diff with the stored season_totals.json."""
import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime import season_evidence as se
root = Path('/home/user/stone-basketball-career')
season = sys.argv[1]
fresh = se.compute_totals(season, root)
stored = {r['bbr_id']: r for r in json.loads((root / se.totals_path(season)).read_text())['records']}
print('fresh', len(fresh), 'stored', len(stored))
print('fresh-only', [(b, fresh[b]['player_name'], fresh[b]['totals']['games']) for b in fresh if b not in stored])
print('stored-only', [b for b in stored if b not in fresh])
d = [(b, stored[b]['totals']['games'], fresh[b]['totals']['games']) for b in fresh if b in stored and fresh[b]['totals'] != stored[b]['totals']]
print('differ', len(d), d[:10])
