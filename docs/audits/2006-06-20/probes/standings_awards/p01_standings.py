import json, re, glob, os, sys
from collections import defaultdict
R='/home/user/stone-basketball-career'
def results(season):
    out={}
    for note in glob.glob(f'{R}/career/Dwyane_Wade/{season}/06_Regular_Season/**/Game_*.md', recursive=True):
        t=open(note).read()
        m=re.search(r'^status: (\S+)',t,re.M)
        rf=re.search(r'^result_file: (\S+)',t,re.M)
        if not m or m.group(1)!='played' or not rf: continue
        d=json.load(open(os.path.join(os.path.dirname(note),rf.group(1))))
        if d.get('game_type')!='regular' or not d.get('terminated'): print('odd',note); continue
        out[d['event_id']]=d
    for p in glob.glob(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{season}/Games/*.result.json'):
        d=json.load(open(p))
        if d.get('game_type')!='regular' or not d.get('terminated'): continue
        if d['event_id'] in out: print('dup',d['event_id'])
        out[d['event_id']]=d
    return out
def table(season):
    res=results(season)
    t=defaultdict(lambda:[0,0])
    for d in res.values():
        h=d['final_score']['home']>d['final_score']['away']
        assert d['final_score']['home']!=d['final_score']['away']
        t[d['home']][0 if h else 1]+=1
        t[d['away']][1 if h else 0]+=1
    return t,res
def page(season):
    txt=open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{season}/Standings.md').read()
    rows={}
    conf=None; order=defaultdict(list)
    for line in txt.splitlines():
        if line.startswith('## '): conf=line[3:7]
        m=re.match(r'\| (\d+) \| \**([^|*]+?)\** \| (\d+) \| (\d+) \|',line)
        if m: rows[m.group(2)]=(int(m.group(3)),int(m.group(4))); order[conf].append(m.group(2))
    return rows,order
for s in ['2003-04','2004-05','2005-06']:
    t,res=table(s); rows,order=page(s)
    print(s,'games',len(res),'clubs',len(t), 'total W',sum(v[0] for v in t.values()))
    for c in sorted(set(t)|set(rows)):
        if tuple(t.get(c,[0,0]))!=rows.get(c): print('  MISMATCH',c,t.get(c),rows.get(c))
    for c,v in t.items():
        if sum(v)!=82: print('  not 82',c,v)
    # head-to-head ties
    for conf,cl in order.items():
        for a,b in zip(cl,cl[1:]):
            if rows[a]==rows[b]:
                h2h=[0,0]
                for d in res.values():
                    if {d['home'],d['away']}=={a,b}:
                        w=d['home'] if d['final_score']['home']>d['final_score']['away'] else d['away']
                        h2h[0 if w==a else 1]+=1
                print('  tie',conf,a,b,rows[a],'h2h',h2h)
