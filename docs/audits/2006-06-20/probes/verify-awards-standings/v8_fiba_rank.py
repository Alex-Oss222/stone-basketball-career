import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime import national
R = Path('/home/user/stone-basketball-career')
ed = national.editions(R)['continental_qualifier_2005']
rec = national.read_record(ed, R)
rank = national.final_ranking(ed, rec, R)
print('code ranking', rank)
print('stored', rec['ranking'])
closed = national.results(ed, rec, R)
# recompute group records from results
from collections import defaultdict
rec_by = defaultdict(lambda: [0,0,0,0])
for n, r in closed.items():
    if r['stage'] in ('group_A','group_B'):
        h, a = r['home'], r['away']
        hs, as_ = r['home_score'], r['away_score']
        rec_by[(r['stage'],h)][0 if hs>as_ else 1]+=1
        rec_by[(r['stage'],a)][0 if as_>hs else 1]+=1
        rec_by[(r['stage'],h)][2]+=hs-as_; rec_by[(r['stage'],a)][2]+=as_-hs
for k in [('group_A','Venezuela'),('group_B','Uruguay')]:
    print(k, rec_by[k])
