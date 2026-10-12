"""FIBA 2005 Americas: each result's own home/away/final_score against tournament.json's game entry and the
README game table; and box sums."""
import json, re, glob
R = '/home/user/stone-basketball-career/career/Dwyane_Wade/FIBA/Continental_Cups/2005'
rec = json.load(open(R + '/tournament.json'))
page = open(R + '/README.md').read()
rows = {int(m[0]): m for m in re.findall(r'^\| (\d+) \| (\S+) \| ([^|]+) \| ([^|]+) \| (\d+)-(\d+) \| \[box\]\(Games/([^)]+)\) \|$', page, re.M)}
for num, g in sorted(rec['games'].items(), key=lambda kv: int(kv[0])):
    res = json.load(open(R + '/Games/' + f"fiba-amc05-g{int(num):02d}.result.json"))
    req = json.load(open(R + '/Games/' + f"fiba-amc05-g{int(num):02d}.request.json"))
    winner = res['home'] if res['final_score']['home'] > res['final_score']['away'] else res['away']
    sums = {s: sum(p['pts'] for p in res['player_stats'][s]) for s in ('home', 'away')}
    r = rows[int(num)]
    page_home, page_away, ph, pa = r[2].strip(), r[3].strip(), int(r[4]), int(r[5])
    page_winner = page_home if ph > pa else page_away
    rec_keys = {k: g.get(k) for k in ('home', 'away', 'home_score', 'away_score', 'stage', 'winner') if k in g}
    flag = []
    if page_winner != winner: flag.append('PAGE WINNER WRONG')
    if sums['home'] != res['final_score']['home'] or sums['away'] != res['final_score']['away']: flag.append('BOX SUM')
    if (res['home'], res['away']) != (page_home, page_away): flag.append('SIDES DIFFER')
    print(num, g.get('stage'), 'result:', res['home'], res['final_score']['home'], '-', res['away'], res['final_score']['away'],
          '| page:', page_home, ph, '-', page_away, pa, '| req:', req.get('home', {}).get('team') if isinstance(req.get('home'), dict) else req.get('home'),
          '| rec:', rec_keys, flag)
