import sys, re, json, glob
sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime.league_cards import age_on
R='/home/user/stone-basketball-career'
B='1984-03-24'
# playoff game dates for Toronto per season from the league playoff games
for s in ('2003-04','2004-05','2005-06'):
    dates=[]
    for f in glob.glob(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/Playoffs/Games/*.result.json'):
        d=json.load(open(f)); r=d.get('result',d)
        if 'Toronto Raptors' in (r.get('home'),r.get('away')): dates.append(r.get('game_date') or r.get('date'))
    dates=[x for x in dates if x]
    print(s,'playoff games',len(dates), min(dates) if dates else None, max(dates) if dates else None,
          'ages', sorted({age_on(B,x) for x in dates}), 'Nov1 age', age_on(B,s[:4]+'-11-01'),
          'season cutoff age', age_on(B,min('2006-06-20',f'{int(s[:4])+1}-06-30')))
for f in [f'{R}/career/Chris_Bosh/README.md']+sorted(glob.glob(f'{R}/career/Chris_Bosh/20*/README.md')):
    for l in open(f):
        m=re.match(r'^\| \[?(20\d\d-\d\d)\]?[^|]*\| (\d+) \| Toronto',l)
        if m: print(f.split('career/')[1], m.group(1), m.group(2))
for s in ('2003-04','2004-05','2005-06'):
    t=open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/League_Stats.md').read()
    m=re.search(r'\[Chris Bosh\]\([^)]*\) \| (\d+) \|',t); print('League season page',s,m.group(1))
