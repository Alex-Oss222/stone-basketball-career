"""For every closed regular and playoff game of 2004-05 and 2005-06, check that each box player's side equals
runtime.club_truth.holder(bbr_id, name, game_date). Players mapped to bbr via the request's frozen inputs."""
import sys, json, collections, time
sys.path.insert(0, '/home/user/stone-basketball-career')
sys.path.insert(0, '/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/completeness')
from results_lib import results, bbr_map
from runtime import club_truth
from runtime.player_stats import alias
ROOT = '/home/user/stone-basketball-career'
t0 = time.time()
out = collections.defaultdict(list)
nchecked = 0
for season in sys.argv[1:]:
    for kind in ('regular', 'playoff'):
        for p, d, req in results(season, kind):
            for side in ('home', 'away'):
                team = d[side]
                m = bbr_map(req, side)
                for row in d['player_stats'].get(side, []):
                    name = row['player_id']
                    if not ((row.get('seconds') or 0) > 0 or row.get('appeared')):
                        continue
                    bbr = m.get(name)
                    if team == 'Miami Heat' and not bbr:
                        bbr = None
                    try:
                        club, basis = club_truth.holder(bbr, name if team == 'Miami Heat' or not bbr else None, d['game_date'], ROOT)
                    except Exception as e:
                        club, basis = 'ERR', repr(e)
                    nchecked += 1
                    if club != team:
                        out[(season, name, bbr, team, club)].append((d['game_date'], kind, d['event_id'], basis[:90]))
print('checked', nchecked, 'mismatch groups', len(out), 'secs', round(time.time() - t0))
for k, v in sorted(out.items(), key=lambda kv: kv[1][0][0]):
    print(k, len(v), v[0][0], v[-1][0], v[0][1], v[0][3])
