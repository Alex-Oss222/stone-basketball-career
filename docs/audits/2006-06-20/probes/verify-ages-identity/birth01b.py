import json, glob, os, collections, unicodedata, re
exec(open('birth01.py').read().split("print('records'")[0])
by=collections.defaultdict(lambda: collections.defaultdict(set))
for r in recs:
    bb=r['bbr'] if isinstance(r['bbr'],str) else (r['bbr'].get('value') if isinstance(r['bbr'],dict) else None)
    key=bb or ('N:'+norm(r['name']) if r['name'] else None)
    if key: by[key][r['birth']].add(r['file'].split('/')[-1])
# also link name to bbr
name2bbr={}
for r in recs:
    bb=r['bbr'] if isinstance(r['bbr'],str) else (r['bbr'].get('value') if isinstance(r['bbr'],dict) else None)
    if bb and r['name']: name2bbr[norm(r['name'])]=bb
merged=collections.defaultdict(lambda: collections.defaultdict(set))
for k,v in by.items():
    kk=name2bbr.get(k[2:],k) if k.startswith('N:') else k
    for b,fs in v.items(): merged[kk][b]|=fs
conf={k:v for k,v in merged.items() if len(v)>1}
print(len(conf))
for k,v in sorted(conf.items()): print(k, {b:sorted(f)[:4] for b,f in v.items()})
