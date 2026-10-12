"""Injured-list entries: Miami games missed between placement and activation against minimum_games, and overlap
(at most three listed at once)."""
import sys, json, glob, collections
W = '/home/user/stone-basketball-career/career/Dwyane_Wade'
for s in ('2003-04', '2004-05', '2005-06'):
    d = json.load(open(f'{W}/{s}/00_Team/Transactions/injured_list.json'))
    games = sorted({json.load(open(p))['game_date'] for p in glob.glob(f'{W}/{s}/06_Regular_Season/**/Game_*.result.json', recursive=True)})
    for e in d['entries']:
        act = e.get('activated') or '9999'
        missed = [g for g in games if e['placed'] <= g < act]
        if len(missed) < (e.get('minimum_games') or 0):
            print(s, 'SHORT', e['player'], e['placed'], e.get('activated'), len(missed), e.get('minimum_games'))
    over = collections.Counter()
    for g in games:
        n = sum(1 for e in d['entries'] if e['placed'] <= g < (e.get('activated') or '9999'))
        if n > 3:
            over[g] = n
    print(s, 'entries', len(d['entries']), 'days with >3 listed', dict(list(over.items())[:5]), len(over))
