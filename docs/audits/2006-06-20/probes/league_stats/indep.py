"""Independent aggregation of regular-season league lines from raw closed results.
Matching: bbr_id from the committed request (Miami: request players; league: frozen stat_profile.bbr_id), else exact registry name."""
import json, re, glob, sys
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
LEAGUE = ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League'
CNT = ['pts','fgm','fga','tpm','tpa','ftm','fta','orb','drb','ast','stl','blk','tov','pf']

def front(path):
    t = Path(path).read_text()
    m = re.match(r"^---\n(.*?)\n---", t, re.S)
    meta = {}
    if m:
        for l in m.group(1).splitlines():
            if ':' in l:
                k, v = l.split(':', 1); meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta

def req_bbr(req, side):
    out = {}
    if not req: return out
    s = req.get(side) or {}
    for p in s.get('players', []) if isinstance(s, dict) else []:
        b = p.get('bbr_id') or (p.get('stat_profile') or {}).get('bbr_id')
        if b: out[p['player_id']] = b
    fr = (req.get('frozen') or {}).get(side) or {}
    for p in fr.get('players', []):
        b = p.get('bbr_id') or (p.get('stat_profile') or {}).get('bbr_id')
        if b: out.setdefault(p['player_id'], b)
    return out

def results(season, kinds=('regular',), clock='2006-06-20'):
    rows = []
    base = ROOT / 'career/Dwyane_Wade' / season
    for note in sorted(base.glob('06_Regular_Season/*/Week_*/Game_*.md')) if 'regular' in kinds else []:
        if not re.fullmatch(r'Game_\d+\.md', note.name): continue
        meta = front(note)
        if meta.get('status') != 'played' or not meta.get('result_file'): continue
        rp = note.with_name(meta['result_file'])
        r = json.loads(rp.read_text())
        q = note.with_name(note.stem + '.request.json')
        req = json.loads(q.read_text()) if q.is_file() else None
        rows.append((r, req, 'miami', str(note)))
    for rp in sorted((LEAGUE / season / 'Games').glob('*.result.json')):
        r = json.loads(rp.read_text())
        if r.get('game_type') not in kinds or not r.get('terminated'): continue
        q = rp.with_name(rp.name.replace('.result.json', '.request.json'))
        req = json.loads(q.read_text()) if q.is_file() else None
        rows.append((r, req, 'league', str(rp)))
    rows = [x for x in rows if x[0]['game_date'] <= clock]
    return rows

import unicodedata
def key(name):
    folded = unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z]', '', folded.lower())
alias = {}
try:
    _c = json.loads((ROOT / 'library/careers/nba_player_careers.json').read_text())['players']
    _k = {}
    for b, e in _c.items():
        _k.setdefault(key(e.get('player_name')), set()).add(b)
    alias = {k: next(iter(v)) for k, v in _k.items() if len(v) == 1}
    alias.update({'stanislavmedvedenko': 'medvest01', 'mettaworldpeace': 'artesro01'})
except Exception as e:
    print('alias load failed', e)

def registry():
    reg = json.loads((LEAGUE / 'player_registry.json').read_text())['players']
    return reg

def lines(season, kinds=('regular',), rows=None):
    reg = registry()
    by_bbr = {p['bbr_id']: p for p in reg}
    by_name = {p['name']: p for p in reg}
    by_key = {key(p['name']): p for p in reg}
    out = {}
    unmatched = []
    for r, req, src, path in (rows if rows is not None else results(season, kinds)):
        for side in ('home', 'away'):
            other = 'away' if side == 'home' else 'home'
            ids = req_bbr(req, side)
            for row in r['player_stats'][side]:
                pid = row['player_id']
                b = ids.get(pid)
                p = by_bbr.get(b) if b else None
                via = 'bbr'
                if p is None:
                    p = by_name.get(pid); via = 'name'
                if p is None:
                    p = by_key.get(key(pid)); via = 'key'
                if p is None and key(pid) in alias:
                    p = by_bbr.get(alias[key(pid)]); via = 'alias'
                if p is None:
                    unmatched.append((pid, r[side], r['event_id'])); continue
                if b and p['bbr_id'] != b:
                    unmatched.append(('MISMATCH', pid, b, p['bbr_id']))
                app = row.get('appeared', row['seconds'] > 0 or any(row[k] for k in CNT))
                rec = dict(date=r['game_date'], event=r['event_id'], club=r[side], appeared=app, started=row.get('started'),
                           seconds=row['seconds'], via=via, bbr_req=b, **{k: row[k] for k in CNT})
                out.setdefault(p['name'], []).append(rec)
    return out, unmatched

def agg(recs, start, end):
    rs = [x for x in recs if start <= x['date'] <= end and x['appeared']]
    g = len(rs)
    t = {k: sum(x[k] for x in rs) for k in CNT}
    t['sec'] = sum(x['seconds'] for x in rs)
    gs = sum(1 for x in rs if x['started']) if rs and all(x['started'] is not None for x in rs) else None
    return g, gs, t

def fmt(g, gs, t):
    def n(v): return 'N/A' if v is None else f"{v:.1f}"
    def r(a, b): return 'N/A' if not b else f"{a/b:.3f}".removeprefix('0')
    pg = (lambda v: v / g) if g else (lambda v: None)
    fgm, fga, tpm, tpa, ftm, fta = (t[k] for k in ('fgm','fga','tpm','tpa','ftm','fta'))
    cells = {
        'G': str(g), 'GS': 'N/A' if gs is None else str(gs), 'MP': n(pg(t['sec'] / 60)),
        'FG': n(pg(fgm)), 'FGA': n(pg(fga)), 'FG%': r(fgm, fga), '3P': n(pg(tpm)), '3PA': n(pg(tpa)), '3P%': r(tpm, tpa),
        '2P': n(pg(fgm - tpm)), '2PA': n(pg(fga - tpa)), '2P%': r(fgm - tpm, fga - tpa), 'eFG%': r(fgm + .5 * tpm, fga),
        'FT': n(pg(ftm)), 'FTA': n(pg(fta)), 'FT%': r(ftm, fta), 'ORB': n(pg(t['orb'])), 'DRB': n(pg(t['drb'])),
        'TRB': n(pg(t['orb'] + t['drb'])), 'AST': n(pg(t['ast'])), 'STL': n(pg(t['stl'])), 'BLK': n(pg(t['blk'])),
        'TOV': n(pg(t['tov'])), 'PF': n(pg(t['pf'])), 'PTS': n(pg(t['pts'])), 'TS% (est.)': r(t['pts'], 2 * (fga + .44 * fta)),
    }
    return cells
