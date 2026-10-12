"""Independent playoff aggregation vs League/<season>/Playoffs/Playoff_Stats.md (all-games table and per-round tables)."""
import sys, re, json
sys.path.insert(0, '.')
import indep
from pathlib import Path
from collections import defaultdict
season = sys.argv[1]
ROOT = indep.ROOT; LEAGUE = indep.LEAGUE
reg = indep.registry(); by_bbr = {p['bbr_id']: p['name'] for p in reg}
close = json.loads((ROOT / f'career/Dwyane_Wade/{season}/season_close.json').read_text())['close_date'] if (ROOT / f'career/Dwyane_Wade/{season}/season_close.json').is_file() else '2006-06-20'
now = min('2006-06-20', close)
rows = []
for note in sorted((ROOT / f'career/Dwyane_Wade/{season}/08_Playoffs').rglob('Game_*.md')):
    if not re.fullmatch(r'Game_\d+\.md', note.name): continue
    meta = indep.front(note)
    if meta.get('status') != 'played' or not meta.get('result_file'): continue
    r = json.loads(note.with_name(meta['result_file']).read_text())
    q = note.with_name(note.stem + '.request.json')
    rows.append((r, json.loads(q.read_text()) if q.is_file() else None, 'miami', str(note)))
for rp in sorted((LEAGUE / season / 'Playoffs/Games').glob('*.result.json')):
    r = json.loads(rp.read_text())
    if r.get('game_type') != 'playoff' or not r.get('terminated'): continue
    q = rp.with_name(rp.name.replace('.result.json', '.request.json'))
    rows.append((r, json.loads(q.read_text()) if q.is_file() else None, 'league', str(rp)))
rows = [x for x in rows if x[0]['game_date'] <= now]
ids = [x[0]['event_id'] for x in rows]
assert len(ids) == len(set(ids)), 'dup'
print('closed playoff games', len(rows), 'miami', sum(1 for x in rows if x[2] == 'miami'), 'now', now)
rec = json.loads((LEAGUE / season / 'playoffs.json').read_text())
rnd = {g['event_id']: s['round'] for s in rec['series'] for g in s['games'] if g.get('event_id')}
missing_round = [i for i in ids if i not in rnd]
print('games without a round in playoffs.json', len(missing_round), missing_round[:3])
series_games = sum(len([g for g in s['games'] if g.get('event_id')]) for s in rec['series'])
print('series games with event ids', series_games)
CNT = indep.CNT
lines = defaultdict(list)
for r, req, src, path in rows:
    for side in ('home', 'away'):
        ids_ = indep.req_bbr(req, side)
        for row in r['player_stats'][side]:
            b = ids_.get(row['player_id'])
            name = by_bbr.get(b) or row['player_id']
            app = row.get('appeared', row['seconds'] > 0 or any(row[k] for k in CNT))
            if not app: continue
            lines[(name, r[side])].append(dict(event=r['event_id'], started=row.get('started'), seconds=row['seconds'], **{k: row[k] for k in CNT}))
def fmt(name, club, rs):
    g = len(rs); t = {k: sum(x[k] for x in rs) for k in CNT}; sec = sum(x['seconds'] for x in rs)
    gs = sum(1 for x in rs if x['started'])
    p = lambda a, b: 'N/A' if not b else ('1.000' if a / b >= 1 else f"{a/b:.3f}".lstrip('0'))
    n = lambda v: f"{v/g:.1f}"
    return [name, club, str(g), str(gs), n(sec / 60), n(t['pts']), n(t['orb'] + t['drb']), n(t['ast']), n(t['stl']), n(t['blk']), n(t['tov']),
            f"{t['fgm']}-{t['fga']}", p(t['fgm'], t['fga']), f"{t['tpm']}-{t['tpa']}", p(t['tpm'], t['tpa']), f"{t['ftm']}-{t['fta']}", p(t['ftm'], t['fta']),
            p(t['pts'], 2 * (t['fga'] + .44 * t['fta']))]
page = (LEAGUE / season / 'Playoffs/Playoff_Stats.md').read_text()
sections = re.split(r'^## ', page, flags=re.M)
labels = {'All playoff games': None, 'First round': 'first_round', 'Conference semifinals': 'conference_semifinals', 'Conference finals': 'conference_finals', 'NBA Finals': 'finals'}
bad = 0; checked = 0
for sec in sections[1:]:
    title = sec.split('\n', 1)[0].strip()
    key = labels.get(title, 'UNKNOWN')
    table = [l for l in sec.splitlines() if l.startswith('|')][2:]
    got = {}
    for l in table:
        c = [x.strip() for x in l.strip().strip('|').split('|')]
        got[(c[0], c[1])] = c
    exp = {}
    for (name, club), rs in lines.items():
        rs2 = [x for x in rs if key is None or rnd.get(x['event']) == key]
        if rs2: exp[(name, club)] = fmt(name, club, rs2)
    for k in set(got) | set(exp):
        checked += 1
        if got.get(k) != exp.get(k):
            bad += 1
            if bad <= 15: print(title, k, '\n   page', got.get(k), '\n   mine', exp.get(k))
print('rows checked', checked, 'mismatches', bad)
