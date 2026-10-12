"""Interactive league cards (HTML, embedded player-card-data JSON): the 2005-06 'season' period's appearances and
box totals against an independent bbr aggregation of the closed regular-season results; identity age and team."""
import sys, json, re, glob, collections, os
sys.path.insert(0, '/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/completeness')
from results_lib import results, bbr_map, L
reg = json.load(open(L + '/player_registry.json'))
reg = reg['players'] if isinstance(reg, dict) else reg
by_rid = {p['registry_id']: p for p in reg}
ind = collections.defaultdict(lambda: collections.Counter())
for p, d, req in results('2005-06', 'regular'):
    for side in ('home', 'away'):
        m = bbr_map(req, side)
        for row in d['player_stats'][side]:
            b = m.get(row['player_id']) or ('wadedw01' if row['player_id'] == 'Dwyane Wade' else None)
            if not b:
                continue
            if (row.get('seconds') or 0) > 0 or row.get('appeared'):
                t = ind[b]; t['g'] += 1
                for k in ('pts', 'fgm', 'fga', 'tpm', 'tpa', 'ftm', 'fta', 'orb', 'drb', 'ast', 'stl', 'blk', 'tov', 'pf'):
                    t[k] += row[k]
keys_seen = None; bad = []; n = 0
for f in sorted(glob.glob(L + '/Players/*.html')):
    rid = os.path.basename(f)[:-5]
    p = by_rid.get(rid)
    if not p:
        continue
    t = open(f, encoding='utf-8').read()
    m = re.search(r'<script id="player-card-data" type="application/json">(.*?)</script>', t, re.S)
    d = json.loads(m.group(1))
    per = next((x for x in d['periods'] if x['id'] == 'season'), None)
    if per is None:
        bad.append((rid, 'no season period')); continue
    box = per.get('box') or {}
    keys_seen = keys_seen or list(box.keys())
    exp = ind.get(p.get('bbr_id'), collections.Counter())
    n += 1
    if per.get('appearances') != exp['g']:
        bad.append((rid, 'appearances', per.get('appearances'), exp['g']))
    for k in ('pts', 'fgm', 'fga', 'tpm', 'tpa', 'ftm', 'fta', 'orb', 'drb', 'ast', 'stl', 'blk', 'tov', 'pf'):
        if k in box and box[k] != exp[k]:
            bad.append((rid, k, box[k], exp[k])); break
print('cards', n, 'box keys', keys_seen, 'issues', len(bad))
for b in bad[:20]:
    print(b)
