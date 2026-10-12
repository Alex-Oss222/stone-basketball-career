import re, sys, glob
sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime.stat_milestones import age_text
ROOT='/home/user/stone-basketball-career'
births={'Dwyane_Wade':'1984-01-17','Chris_Bosh':'1984-03-24'}
bad=[]; n=0
for who,b in births.items():
    for f in glob.glob(f'{ROOT}/career/{who}/**/*.md',recursive=True):
        if '/Stats_and_Awards/League/' in f or '/Team/' in f or '/00_Team/' in f: continue
        for line in open(f):
            for m in re.finditer(r'(\d{4}-\d{2}-\d{2})\S* \| (\d+ years, \d+ days?)',line):
                n+=1
                if age_text(b,m.group(1))!=m.group(2): bad.append((f.replace(ROOT+'/',''),m.group(1),m.group(2),age_text(b,m.group(1))))
print(n, len(bad)); print(bad[:10])
