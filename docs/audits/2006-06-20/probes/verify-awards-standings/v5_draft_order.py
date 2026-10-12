import json
from pathlib import Path
R = Path('/home/user/stone-basketball-career/career/Dwyane_Wade')
for f in ['2004-05/09_Draft/draft_order_2005.json', '2005-06/09_Draft/draft_order_2006.json']:
    j = json.loads((R/f).read_text())
    seeds = j['lottery_seeds']
    picks = j['picks']
    r1 = [p for p in picks if p['round'] == 1]; r2 = [p for p in picks if p['round'] == 2]
    print(f, 'lottery clubs', len(seeds), 'r1 picks', len(r1), 'r2 picks', len(r2))
    print('  CHA seed', [s for s in seeds if s['club'].startswith('Charlotte')])
    print('  winners', j['lottery_winners'])
    print('  CHA picks', [(p['pick'], p['round']) for p in picks if p['original'] == 'CHA'])
    print('  MIN picks', [(p['pick'], p['round'], p['owner']) for p in picks if p['original'] == 'MIN'])
    print('  rule mentions: 13 clubs', '13 clubs' in j['rule'], '| No. 4', 'No. 4' in j['rule'], '| Minnesota forfeited', 'forfeited' in j['rule'], '| 29 clubs', '29 clubs' in j['rule'], '| No. 33', 'No. 33' in j['rule'], '| later drafts para', 'Every later draft' in j['rule'])
    print('  rule starts with title?', j['rule'][:40])
