import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/completeness')
from results_lib import results, bbr_map
season, target = sys.argv[1], sys.argv[2]
for p, d, req in results(season, 'regular'):
    for side in ('home', 'away'):
        m = bbr_map(req, side)
        for row in d['player_stats'][side]:
            if m.get(row['player_id']) == target:
                print(d['event_id'], side, repr(row['player_id']), row.get('seconds'), p.split('/career/')[1][:60])
