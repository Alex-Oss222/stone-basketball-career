"""trajectory_feedback.json <applies_to>: each player's 'minutes' against his closed regular-season seconds in
<from_season>, matched by bbr_id from the requests' frozen inputs; and players with closed minutes and a
trajectory who are missing from the file."""
import sys, json, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
sys.path.insert(0, '/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/completeness')
from results_lib import results, bbr_map, W
from runtime.trajectories import load_trajectories, alternate
ROOT = '/home/user/stone-basketball-career'
for frm, to in [tuple(x.split(':')) for x in (sys.argv[1:] or ['2004-05:2005-06', '2005-06:2006-07'])]:
    secs = collections.Counter(); games = collections.Counter(); unmapped = collections.Counter(); clubs = collections.defaultdict(set)
    for p, d, req in results(frm, 'regular'):
        for side in ('home', 'away'):
            m = bbr_map(req, side)
            for row in d['player_stats'][side]:
                if not row.get('seconds'):
                    continue
                b = m.get(row['player_id'])
                if not b:
                    unmapped[(d[side], row['player_id'])] += 1
                    continue
                secs[b] += row['seconds']; games[b] += 1; clubs[b].add(d[side])
    fb = json.load(open(f'{W}/{to}/trajectory_feedback.json'))['players']
    tr = load_trajectories(ROOT, frm)
    print(frm, '->', to, 'players with minutes', len(secs), 'feedback players', len(fb), 'unmapped rows', sum(unmapped.values()), list(unmapped.items())[:5])
    bad = [(b, round(secs[b] / 60, 1), fb[b]['minutes']) for b in fb if abs(round(secs[b] / 60, 1) - fb[b]['minutes']) > 0.05]
    print('  minutes mismatches', len(bad), bad[:15])
    missing = [(b, round(secs[b] / 60, 1), games[b], sorted(clubs[b])) for b in secs if b not in fb and tr.has(b, frm)]
    print('  missing with trajectory', len(missing), sorted(missing, key=lambda x: -x[1])[:20])
    excl = [(b, round(secs[b] / 60, 1)) for b in secs if b not in fb and not tr.has(b, frm)]
    print('  no trajectory (excluded by design)', len(excl), sorted(excl, key=lambda x: -x[1])[:15])
    extra = [b for b in fb if b not in secs]
    print('  in feedback without closed minutes', extra[:10])
