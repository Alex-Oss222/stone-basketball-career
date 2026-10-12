"""Independent listing of closed results (no repo generator code)."""
import json, glob, os
R = '/home/user/stone-basketball-career'
W = R + '/career/Dwyane_Wade'
L = W + '/Stats_and_Awards/League'

def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def results(season, kind):
    """kind: 'regular' or 'playoff'. Returns list of (path, result dict, request dict or None)."""
    out = []
    if kind == 'regular':
        miami = glob.glob(f'{W}/{season}/06_Regular_Season/**/Game_*.result.json', recursive=True)
        league = glob.glob(f'{L}/{season}/Games/*.result.json')
    else:
        miami = glob.glob(f'{W}/{season}/08_Playoffs/**/Game_*.result.json', recursive=True)
        league = glob.glob(f'{L}/{season}/Playoffs/Games/*.result.json')
    for p in sorted(miami + league):
        d = load(p)
        if d.get('game_type') not in (kind, None) and not (kind == 'playoff' and d.get('game_type') in ('playoff', 'playoffs')):
            continue
        req = p.replace('.result.json', '.request.json')
        out.append((p, d, load(req) if os.path.exists(req) else None))
    return out

def bbr_map(req, side):
    """name -> bbr from frozen inputs or roster in request."""
    m = {}
    if not req:
        return m
    fr = (req.get('frozen') or {}).get(side) or {}
    for pl in fr.get('players', []):
        sp = pl.get('stat_profile') or {}
        if sp.get('bbr_id'):
            m[pl['player_id']] = sp['bbr_id']
    # older requests
    side_d = req.get(side) or {}
    for pl in side_d.get('players', []) if isinstance(side_d, dict) else []:
        if isinstance(pl, dict) and pl.get('bbr_id'):
            m[pl.get('player_id') or pl.get('name')] = pl['bbr_id']
    return m
