import re, glob, json, collections, sys
sys.path.insert(0,'/home/user/stone-basketball-career')
R='/home/user/stone-basketball-career'
# rotation in force for Wade by date: reviews + camp
plan=[]
for s in ('2003-04','2004-05','2005-06'):
    for f in sorted(glob.glob(f'{R}/career/Dwyane_Wade/{s}/00_Team/Team/Depth_Chart/Reviews/*/rotation.json')):
        d=json.load(open(f)); day=f.split('/')[-2]
        m=next((p.get('minutes') for p in d['players'] if p.get('player_id')=='Dwyane Wade'),None)
        plan.append((day,m))
plan.sort()
def plan_on(day):
    x=[m for d,m in plan if d<=day]; return x[-1] if x else None
blocks=0; stale=collections.Counter(); files=set(); ex=[]
for f in glob.glob(f'{R}/career/Dwyane_Wade/**/*.md',recursive=True):
    t=open(f).read()
    for m in re.finditer(r'\| Role \| ([^|]+) \|.*?Identity as of (\d{4}-\d{2}-\d{2})',t,re.S):
        role, day = m.group(1).strip(), m.group(2)
        blocks+=1
        mm=re.search(r'staff plan ([\d.]+) minutes',role)
        p=plan_on(day)
        # camp reviews reset plan: 2004-10-28 (34) and 2005-10-26 (34)
        for camp in ('2004-10-28','2005-10-26'):
            pass
        if mm and p is not None and abs(float(mm.group(1))-p)>0.5:
            # ignore window between camp snapshot and first review of season
            if ('2004-10-28'<=day<'2004-11-11') or ('2005-10-26'<=day<'2005-11-09'): continue
            stale[day[:7]]+=1; files.add(f); ex.append((f.replace(R+'/',''),day,role,p))
print('role blocks',blocks,'stale blocks',sum(stale.values()),'files',len(files))
print(sorted(stale.items()))
print(ex[:3]); print([e for e in ex if e[1]>='2006-06'][:3])
print(plan[-3:], [p for p in plan if p[0].startswith('2004-11') or p[0].startswith('2005-04')])
