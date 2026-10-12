import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime.career_stats import collect_games
R = Path('/home/user/stone-basketball-career/career/Dwyane_Wade')
ident = json.loads((R/'professional_identity.json').read_text())
recs = collect_games(R, ident, '2006-06-20')
from collections import Counter
print(Counter((r['coverage'], r['appearance']) for r in recs if r['status']=='played'))
for r in recs:
    if r['status']=='played' and r['coverage']!='complete':
        print(r['date'], r['competition'], r['season'], r['result'], r.get('win'), r['venue'], r['team'], Path(r['note']).relative_to(R))
