import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/completeness')
from bosh import lines, agg, fmt
reg, po = [], []
for s in ('2003-04', '2004-05', '2005-06'):
    reg += lines(s, 'regular'); po += lines(s, 'playoff')
print('career regular', fmt(agg(reg)))
print('career playoff', fmt(agg(po)))
for s in ('2003-04', '2004-05', '2005-06'):
    r = [x for x in lines(s, 'regular')]
    fg = max(x['fgm'] for x in r); hits = [x for x in r if x['fgm'] == fg]
    mn = max(int(x['seconds'] // 60) for x in r); mh = [x for x in r if int(x['seconds'] // 60) == mn]
    print(s, 'FG high', fg, hits[0]['date'], hits[0]['opp'], len(hits) - 1, 'MIN high', mn, mh[0]['date'], mh[0]['opp'], len(mh) - 1, round(max(x['seconds'] for x in r) / 60, 2))
