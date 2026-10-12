import sys, json; sys.path.insert(0, '.')
from wade_games import wade_rows, fm
from pathlib import Path
for note, f, res, row in wade_rows('2003-04', '05_Preseason'):
    req = note.with_suffix('.request.json')
    rq = json.loads(req.read_text()) if req.exists() else None
    in_req = None
    if rq:
        s = json.dumps(rq)
        in_req = 'Dwyane Wade' in s
    inact = res and any('Dwyane Wade' in v for v in res.get('inactive', {}).values())
    absn = res and [a for a in res.get('absences', []) if a.get('player_id') == 'Dwyane Wade']
    miami_side = None
    if res:
        miami_side = 'home' if res['home'] == 'Miami Heat' or 'Miami' in str(res.get('home')) else 'away'
    print(note.name, f.get('date'), f.get('result'), '| in request', in_req, '| row', bool(row), (row or {}).get('pts'), round((row or {}).get('seconds', 0)/60, 1), '| inactive', inact, absn)
