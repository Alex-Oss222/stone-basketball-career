import json, re
R='/home/user/stone-basketball-career'
def league_rows(s):
    rows={}
    cols=None
    for line in open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/League_Stats.md'):
        if line.startswith('| Player |'): cols=[c.strip() for c in line.strip().strip('|').split('|')]
        m=re.match(r'\| \[([^\]]+)\]\(\.\./Players/([^)]+)\.md\)',line)
        if m and cols:
            vals=[c.strip() for c in line.strip().strip('|').split('|')]
            d=dict(zip(cols,vals)); d['_id']=m.group(2)
            if m.group(1) in rows: print('dup row',s,m.group(1))
            rows[m.group(1)]=d
    return rows
def num(v):
    try: return float(v)
    except: return None
for s in ['2003-04','2004-05','2005-06']:
    L=league_rows(s)
    sa=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/season_awards.json'))
    n=0
    for x in sa['decisions']:
        if x['award'] in('coy','finals_mvp'): continue
        people=list(x.get('tally') or [])
        for t in x.get('teams') or []: people+=t['players']
        for p in people:
            if 'games' not in p: continue
            r=L.get(p['player'])
            if r is None: print(s,x['award'],'no League_Stats row for',p['player']); continue
            n+=1
            checks={'G':('games',0),'MP':('mpg',1),'TRB':('reb',1),'AST':('ast',1),'STL':('stl',1),'BLK':('blk',1),'PTS':('pts',1)}
            for col,(k,_) in checks.items():
                if num(r.get(col))!=p.get(k): print(s,x['award'],p['player'],col,'page',r.get(col),'award',p.get(k))
            if 'starts' in p and num(r.get('GS'))!=p['starts']: print(s,x['award'],p['player'],'GS',r.get('GS'),'starts',p['starts'])
            if x['award']=='smoy' and p['starts']*2>=p['games']: print(s,'smoy started too many',p)
    print(s,'checked',n)
