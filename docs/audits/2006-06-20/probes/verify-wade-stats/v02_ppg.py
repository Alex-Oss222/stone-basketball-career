import sys; sys.path.insert(0, '.')
from wade_games import wade_rows
for s in ['2003-04', '2004-05', '2005-06']:
    rows = wade_rows(s, '06_Regular_Season')
    played = [r for r in rows if r[2] is not None]
    app = [r for r in played if r[3] and (r[3]['seconds'] > 0 or r[3].get('appeared'))]
    pts = sum(r[3]['pts'] for r in app)
    mins = sum(r[3]['seconds'] for r in app)/60
    print(s, 'notes', len(rows), 'played', len(played), 'G', len(app), 'PTS', pts, 'PPG', round(pts/len(app), 2), 'MIN', round(mins, 1))
