"""Independent collection of every Wade game from closed notes + declared result files."""
import json, os, re, sys
from pathlib import Path
REPO = Path('/home/user/stone-basketball-career')
CAREER = REPO / 'career/Dwyane_Wade'
STATS = ['seconds','pts','fgm','fga','tpm','tpa','ftm','fta','orb','drb','ast','stl','blk','tov','pf']

def front(path):
    t = path.read_text()
    m = re.match(r'^---\n(.*?)\n---\n', t, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip()
    return meta

def collect():
    games = []
    issues = []
    for season in sorted(p.name for p in CAREER.iterdir() if re.match(r'\d{4}-\d{2}$', p.name)):
        root = CAREER / season
        for note in sorted(root.rglob('Game_*.md')):
            rel = note.relative_to(CAREER)
            parts = rel.parts
            phase = parts[1]
            if phase not in ('05_Preseason', '06_Regular_Season', '08_Playoffs', '11_All_Star', '02_Summer_League', '07_Play_In_Tournament'):
                continue
            meta = front(note)
            st = meta.get('status')
            rf = meta.get('result_file')
            res_path = note.parent / rf if rf else None
            # check result file beside note exists even if not declared
            sib = note.with_suffix('').as_posix() + '.result.json'
            if st != 'played':
                if Path(sib).exists():
                    issues.append(('result_without_played_note', str(rel), st))
                games.append(dict(season=season, phase=phase, note=str(rel), status=st, meta=meta, row=None))
                continue
            if not res_path or not res_path.exists():
                issues.append(('played_without_result', str(rel)))
                continue
            d = json.loads(res_path.read_text())
            row = None; side = None
            for s, rows in d['player_stats'].items():
                for r in rows:
                    if r.get('player_id') in ('Dwyane Wade',) or r.get('bbr_id') == 'wadedw01':
                        row = r; side = s
            inactive = d.get('inactive', {})
            inact = any('Dwyane Wade' in (v or []) for v in inactive.values()) if isinstance(inactive, dict) else False
            games.append(dict(season=season, phase=phase, note=str(rel), status=st, meta=meta, row=row, side=side,
                              inactive=inact, game_type=d.get('game_type'), game_date=d.get('game_date'),
                              rseason=d.get('season'), event_id=d.get('event_id'), result=d))
    return games, issues

def appeared(r):
    if r is None: return False
    if r.get('appeared') is True: return True
    return r.get('seconds', 0) > 0 or any(r.get(k, 0) for k in STATS if k != 'seconds')

def agg(rows):
    t = {k: 0 for k in STATS}
    g = gs = 0
    for r in rows:
        if not appeared(r):
            continue
        g += 1
        gs += 1 if r.get('started') else 0
        for k in STATS:
            t[k] += r.get(k, 0)
    t['g'] = g; t['gs'] = gs
    return t

def line(t):
    g = t['g']
    if not g: return None
    pg = lambda k: t[k] / g
    fg2m = t['fgm'] - t['tpm']; fg2a = t['fga'] - t['tpa']
    pct = lambda a, b: (a / b) if b else None
    return dict(G=g, GS=t['gs'], MP=t['seconds']/60/g, FG=pg('fgm'), FGA=pg('fga'), FGp=pct(t['fgm'], t['fga']),
                TP=pg('tpm'), TPA=pg('tpa'), TPp=pct(t['tpm'], t['tpa']), P2=fg2m/g, P2A=fg2a/g, P2p=pct(fg2m, fg2a),
                eFG=pct(t['fgm'] + 0.5*t['tpm'], t['fga']), FT=pg('ftm'), FTA=pg('fta'), FTp=pct(t['ftm'], t['fta']),
                ORB=pg('orb'), DRB=pg('drb'), TRB=(t['orb']+t['drb'])/g, AST=pg('ast'), STL=pg('stl'), BLK=pg('blk'),
                TOV=pg('tov'), PF=pg('pf'), PTS=pg('pts'), TS=(t['pts']/(2*(t['fga']+0.44*t['fta']))) if (t['fga'] or t['fta']) else None)

if __name__ == '__main__':
    games, issues = collect()
    print('issues', issues)
    from collections import Counter
    c = Counter((g['season'], g['phase'], g['status'], g.get('game_type')) for g in games)
    for k, v in sorted(c.items(), key=lambda x: str(x)): print(k, v)
    for g in games:
        if g['status'] == 'played':
            if g['row'] is None: print('NO WADE ROW', g['note'], 'inactive', g.get('inactive'))
            elif not appeared(g['row']): print('ZERO APPEARANCE', g['note'])
            m = g['meta']
            if m.get('date') != g['game_date']: print('DATE MISMATCH', g['note'], m.get('date'), g['game_date'])
            if m.get('event_id') != g['event_id']: print('EVENT MISMATCH', g['note'])
            if g['rseason'] != g['season']: print('SEASON MISMATCH', g['note'], g['rseason'])
