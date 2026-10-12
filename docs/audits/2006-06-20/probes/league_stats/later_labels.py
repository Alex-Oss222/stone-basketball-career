"""Rows on a season's pages whose Club / rights label comes from a first appearance in a LATER season (registry added_on after the page cutoff)."""
import sys
sys.path.insert(0, '.')
import parse_pages, indep
from compare_pages_lib import scope
reg = {p['name']: p for p in indep.registry()}
for season in ('2003-04', '2004-05'):
    page = indep.LEAGUE / season / 'League_Stats.md'
    s, e = scope(page, season)
    t, g = parse_pages.parse(page)
    rows = [r for x in g.values() for r in x['rows'] if reg[r['name']].get('added_on', '0') > e]
    print(season, 'season page rows labelled from a later first appearance:', len(rows), [(r['name'], r['Club / rights'], reg[r['name']]['added_on']) for r in rows[:6]])
