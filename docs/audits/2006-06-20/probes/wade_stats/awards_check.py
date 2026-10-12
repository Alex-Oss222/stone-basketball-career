"""Cross-check Wade's awards.json against every league decision record that names a winner."""
import json
from pathlib import Path
L = Path('/home/user/stone-basketball-career/career/Dwyane_Wade/Stats_and_Awards/League')
aw = json.load(open('/home/user/stone-basketball-career/career/Dwyane_Wade/awards.json'))['awards']
have = {(a['season'], a['name'], a['period_start'], a['period_end'], a['awarded_on']) for a in aw}
wins = []
for s in ('2003-04', '2004-05', '2005-06'):
    d = json.load(open(L / s / 'award_decisions.json'))
    for x in d['decisions']:
        sl = x.get('shortlist') or []
        winners = [r for r in sl if r.get('rank') == 1 and r.get('winner', True)]
        w = x.get('winner') or (winners[0]['player'] if winners else None)
        if isinstance(w, dict): w = w.get('player')
        if w == 'Dwyane Wade' or any(r['player'] == 'Dwyane Wade' and r.get('rank') == 1 for r in sl):
            wins.append((s, x['name'], x['conference'], x['period_start'], x['period_end'], x['announced_on'], x['id'], x.get('winner')))
for w in wins: print(w)
print(len(wins))
