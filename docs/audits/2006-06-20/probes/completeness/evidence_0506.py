"""season_evidence.compute_totals('2005-06') (the 2006 offseason's front-office evidence, read live since the
season_totals.json file is written at rollover) against independent bbr aggregation from the frozen requests."""
import sys, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
sys.path.insert(0, '/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/completeness')
from pathlib import Path
from results_lib import results, bbr_map
from runtime.season_evidence import compute_totals
root = Path('/home/user/stone-basketball-career')
for season in sys.argv[1:]:
    ct = compute_totals(season, root)
    ind = collections.defaultdict(lambda: [0, 0.0, 0])
    for p, d, req in results(season, 'regular'):
        for side in ('home', 'away'):
            m = bbr_map(req, side)
            for row in d['player_stats'][side]:
                if not (row.get('seconds') or 0) > 0:
                    continue
                b = m.get(row['player_id']) or ('wadedw01' if row['player_id'] == 'Dwyane Wade' else None)
                t = ind[b]; t[0] += 1; t[1] += row['seconds'] / 60; t[2] += row['pts']
    missing = [(b, v[0], round(v[1], 1), v[2]) for b, v in ind.items() if b not in ct]
    diff = [(b, (ct[b]['totals']['games'], ct[b]['totals']['points']), (v[0], v[2])) for b, v in ind.items() if b in ct and (ct[b]['totals']['games'] != v[0] or ct[b]['totals']['points'] != v[2])]
    print(season, 'compute_totals players', len(ct), 'independent', len(ind), 'missing', sorted(missing, key=lambda x: -x[2]), 'diff', diff[:10])
