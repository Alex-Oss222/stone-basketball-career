import json, collections
R = json.load(open('/home/user/stone-basketball-career/career/Dwyane_Wade/Contracts/contract_records.json'))['records']
signed = {}
for r in R:
    if r['event'] == 'signed':
        signed[r['contract_id']] = r
bad = []
for r in R:
    if r['event'] in ('released', 'voided', 'amended', 'assigned'):
        s = signed.get(r['contract_id'])
        if not s:
            bad.append(('no signed record', r['record_id'])); continue
        sd = (r.get('contract') or {}).get('signed_date')
        if sd and s['contract'].get('signed_date') and sd != s['contract']['signed_date']:
            bad.append(('signed_date differs', r['record_id'], r['contract_id'], s['contract'].get('signed_date'), sd))
        # schedule seasons
        ss = set((s['contract'].get('schedule') or {}).keys()); rs = set(((r.get('contract') or {}).get('schedule') or {}).keys())
        if rs and ss and not (rs & ss):
            bad.append(('schedule seasons disjoint', r['record_id'], sorted(ss), sorted(rs)))
for b in bad: print(b)
# players with multiple signed records
per = collections.defaultdict(list)
for r in R:
    if r['event'] == 'signed': per[r['player']].append(r['contract_id'])
print('players with >1 signed record:', {k: v for k, v in per.items() if len(v) > 1})
print(collections.Counter(r['event'] for r in R))
