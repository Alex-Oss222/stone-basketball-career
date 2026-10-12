import sys, json, re, glob, os
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime import league_cards as lc
R='/home/user/stone-basketball-career'
L=R+'/career/Dwyane_Wade/Stats_and_Awards/League'
reg=json.load(open(L+'/player_registry.json'))
players = reg['players'] if isinstance(reg,dict) and 'players' in reg else reg
if isinstance(players, dict): players=list(players.values())
births={p.get('bbr_id') or p.get('id'):p.get('birth_date') for p in players}
print(len(players), list(players[0].keys())[:20])
cs=json.load(open(R+'/career/Dwyane_Wade/2005-06/current_state.json'))
on=cs.get('date') or cs.get('current_date')
print('on',on)
ends={}
for s in ('2003-04','2004-05','2005-06'):
    for p in lc.periods(None, s):
        ends[p['folder']]=p['end']
link=re.compile(r'^\| \[[^\]]*\]\(\.\./([^)]*)/League_Stats\.md\) \| ([^|]*) \|')
tot=bad=0; badcards=set(); samples=[]; hdr_bad=0
for f in sorted(glob.glob(L+'/Players/*.md')):
    pid=os.path.basename(f)[:-3]
    if pid=='README': continue
    b=births.get(pid)
    for line in open(f):
        m=link.match(line)
        if not m: continue
        folder, age = m.group(1), m.group(2).strip()
        if folder not in ends: continue
        tot+=1
        exp=lc.age_on(b, min(ends[folder], on)) if b else None
        exps='N/A' if exp is None else str(exp)
        if exps!=age:
            bad+=1; badcards.add(pid)
            if len(samples)<8 or pid in('wadedw01','abdursh01','jefferal01'): samples.append((pid,folder,age,exps))
print('rows',tot,'bad',bad,'cards',len(badcards),'of',len([x for x in glob.glob(L+'/Players/*.md') if not x.endswith('README.md')]))
for s in samples[:30]: print(s)
