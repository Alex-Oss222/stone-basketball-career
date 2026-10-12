import re
R='/home/user/stone-basketball-career'
for s in ['2003-04','2004-05','2005-06']:
    lead=None
    for line in open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/Standings.md'):
        if line.startswith('## '): lead=None
        m=re.match(r'\| (\d+) \| \**([^|*]+?)\** \| (\d+) \| (\d+) \| (\S+) \| (\S+) \|',line)
        if not m: continue
        w,l=int(m.group(3)),int(m.group(4))
        if lead is None: lead=(w,l)
        gb=((lead[0]-w)+(l-lead[1]))/2
        exp='—' if gb==0 else f'{gb:g}'
        pct=f'{w/(w+l):.3f}'[1:]
        if m.group(6)!=exp or m.group(5)!=pct: print(s,m.group(2),m.group(5),m.group(6),'expected',pct,exp)
    print(s,'ok')
