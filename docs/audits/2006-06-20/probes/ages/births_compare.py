import json, collections, re, unicodedata
S='/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/ages/'
recs=json.load(open(S+'birth_records.json'))
def key(n):
    n=unicodedata.normalize('NFKD',n or '').encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z]','',n)
by=collections.defaultdict(lambda: collections.defaultdict(set))
for r in recs:
    if r['bbr']:
        by[r['bbr']][r['birth']].add(r['file'])
conf={b:v for b,v in by.items() if len(v)>1}
print('bbr ids with conflicting births:',len(conf))
for b,v in sorted(conf.items()):
    print(b, {d:sorted(fs) for d,fs in v.items()})
# name-based for registry players vs all records (name match where bbr missing)
reg=json.load(open('/home/user/stone-basketball-career/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
byname=collections.defaultdict(lambda: collections.defaultdict(set))
for r in recs:
    if isinstance(r['name'],str): byname[key(r['name'])][r['birth']].add(r['file'])
print('--- registry players: name-matched births differing from registry birth (non-FIBA)')
n=0
for p in reg:
    k=key(p['name']); v=byname.get(k,{})
    other={d:fs for d,fs in v.items() if d!=p.get('birth_date')}
    if other:
        n+=1
        print(p['name'],p.get('bbr_id'),p.get('birth_date'),{d:sorted(fs)[:4] for d,fs in other.items()})
print(n)
