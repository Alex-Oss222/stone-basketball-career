import json, glob, os, re, collections
R='/home/user/stone-basketball-career/career/Dwyane_Wade'
rots=[]
for f in glob.glob(f'{R}/*/00_Team/Team/Depth_Chart/rotation.json')+glob.glob(f'{R}/*/00_Team/Team/Depth_Chart/Reviews/*/rotation.json'):
    d=json.load(open(f))
    m=[p.get('minutes') for p in d['players'] if p.get('player_id')=='Dwyane Wade']
    rots.append((d.get('as_of'), m[0] if m else None, f.split('Dwyane_Wade/')[1]))
rots.sort()
for r in rots: pass
print([r[:2] for r in rots if r[0]>='2004'][:4])
def in_force(d):
    c=[r for r in rots if r[0]<=d]
    return c[-1] if c else None
files=[]
for root,_,fs in os.walk(R):
    if '/00_Team' in root or '/Stats_and_Awards/League' in root or '/Stats_and_Awards/Team' in root: continue
    for fn in fs:
        if fn.endswith('.md'): files.append(os.path.join(root,fn))
tot=bad=0; byrange=collections.Counter(); shown=collections.Counter(); badfiles=[]
for f in files:
    t=open(f).read()
    roles=re.findall(r'^\| Role \| ([^|]*) \|', t, re.M)
    if not roles: continue
    m=re.search(r'Identity as of (\d{4}-\d{2}-\d{2})', t)
    if not m: continue
    d=m.group(1)
    for role in roles:
        tot+=1
        mm=re.search(r'staff plan ([\d.]+) minutes', role)
        r=in_force(d)
        if not mm or r is None: continue
        if float(mm.group(1))!=float(r[1]):
            bad+=1; byrange[(r[2].split('/')[0], 'review' if 'Reviews' in r[2] else 'camp')]+=1; shown[role.strip()]+=1; badfiles.append((d,f))
print('role blocks',tot,'mismatch',bad, 'files', len(set(x[1] for x in badfiles)))
print(byrange); print(shown)
ds=sorted(x[0] for x in badfiles); print(ds[0], ds[-1])
# split as auditor: pre 2005-10-26 vs post 2005-11-09
print(sum(1 for d,_ in badfiles if d<'2005-10-26'), sum(1 for d,_ in badfiles if d>='2005-11-09'))
print(sum(1 for d,_ in badfiles if '2005-04-15'<=d<'2005-10-26'), 'in summer 2005 window')
for x in sorted(badfiles)[:3]: print(x)
print([f for d,f in badfiles if 'Professional_Identity' in f or 'trade_update' in f])
