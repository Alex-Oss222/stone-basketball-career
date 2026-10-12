"""Achievement clauses 'At least X points per game while appearing in at least 60 games' judged from closed results."""
import json, re
from compare import games, CAREER
for s in ('2003-04', '2004-05', '2005-06'):
    sc = json.load(open(CAREER / s / 'season_close.json'))
    a = [g['row'] for g in games if g['season'] == s and g['comp'] == 'regular' and g['status'] == 'played' and g['cov'] == 'played']
    pts = sum(r['pts'] for r in a); G = len(a); mins = sum(r['seconds'] for r in a) / 60
    for ev in sc['incentive_evaluation']:
        m = re.search(r'At least ([\d.]+) points per game while appearing in at least (\d+) games', ev['benchmark'])
        if m:
            need, gneed = float(m.group(1)), int(m.group(2))
            exp = 'met' if G >= gneed and pts / G >= need else 'not_met'
            print(s, ev['id'], 'recorded:', ev['status'], '| expected:', exp, f'({pts} pts / {G} G = {pts/G:.2f} PPG; need {need} in >= {gneed} G)', ev['amount'])
        elif 'minutes' in ev['benchmark']:
            print(s, ev['id'], ev['status'], f'{mins:.1f} min')
