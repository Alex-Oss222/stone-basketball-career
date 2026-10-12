"""2003-04 preseason: Wade (signed) absent from Miami's request/result for games 3-7 with no inactive entry."""
import json
from pathlib import Path
P = Path('/home/user/stone-basketball-career/career/Dwyane_Wade/2003-04/05_Preseason')
for i in range(1, 8):
    q = json.loads((P / f'Game_{i}.request.json').read_text()); r = json.loads((P / f'Game_{i}.result.json').read_text())
    side = 'home' if q['home'].get('team') == 'Miami Heat' else 'away'
    dressed = [x['player_id'] for x in q[side]['players']]
    in_box = any(x['player_id'] == 'Dwyane Wade' for x in r['player_stats'][side])
    print(i, q['game_date'], 'in request:', 'Dwyane Wade' in dressed, '| in box:', in_box, '| inactive listed:', 'Dwyane Wade' in r['inactive'][side], '| Miami result:', r['final_score'])
