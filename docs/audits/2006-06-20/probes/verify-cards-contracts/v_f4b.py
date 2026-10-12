import sys, json, os, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from collections import Counter, defaultdict
ROOT = Path('/home/user/stone-basketball-career'); os.chdir(ROOT)
cat = pickle.load(open('cat.pkl' if os.path.exists('cat.pkl') else '/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/verify-cards-contracts/cat.pkl','rb'))
from runtime.club_truth import holder
from runtime.seasons import club_name
reg = {p['registry_id']:p for p in json.load(open('career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
moves = json.load(open('career/Dwyane_Wade/2005-06/League/league_moves.json'))['entries']
mv = defaultdict(list)
for m in moves: mv[m.get('bbr_id')].append(m)
ON='2006-06-20'
mism=[]; cls=Counter()
team_mis=[]
for p in cat['players']:
    r = reg.get(p['id'])
    if not r: continue
    club,_ = holder(r.get('bbr_id'), r['name'], ON)
    if (p['team'] or 'Free agent') != (club or 'Free agent'): team_mis.append((p['id'], p['team'], club))
    c = p['current']
    if not c: continue
    if c['team'] != club:
        # classify by latest league move kind in 2005-06
        ms = sorted(mv.get(r.get('bbr_id'), []), key=lambda m: m['date'])
        kinds = [m['kind'] for m in ms]
        if c['team'] and club and club_name(c['team'], '2005-06') == club: k='rename'
        elif ms: k = ms[-1]['kind']
        else: k='other'
        cls[k]+=1
        mism.append((p['id'], c['team'], club, kinds))
print('current team != holder:', len(mism), cls)
print('profile team != holder:', len(team_mis), team_mis[:10])
for m in mism:
    if m[3]==[] : print('  other', m)
# released/waived Miami camp players now on other clubs with no current contract
no_cur=[]
for p in cat['players']:
    r=reg.get(p['id'])
    if not r or p['current']: continue
    club,_=holder(r.get('bbr_id'), r['name'], ON)
    if club and any(h['team']=='Miami Heat' and h['status'] in ('released','waived') for h in p['history']):
        no_cur.append((p['id'], p['status'], club))
print('released/waived by Miami, no current, now with club:', len(no_cur), no_cur)
# cleared/expired but still current
still=[]
for p in cat['players']:
    r=reg.get(p['id'])
    if not r or not p['current']: continue
    ms=sorted(mv.get(r.get('bbr_id'), []), key=lambda m:m['date'])
    if ms and ms[-1]['kind'] in ('clear','expire') and ms[-1]['date']>= (p['current']['signed_on'] or ''):
        still.append((p['id'], ms[-1]['kind'], ms[-1]['date'], p['current']['id'], p['current']['team']))
print('cleared/expired yet current:', len(still)); [print('  ',s) for s in still]
print('----')
moves4 = json.load(open('career/Dwyane_Wade/2004-05/League/league_moves.json'))['entries'] if os.path.exists('career/Dwyane_Wade/2004-05/League/league_moves.json') else []
mv4=defaultdict(list)
for m in moves4: mv4[m.get('bbr_id')].append(m)
withclub=[m for m in mism if m[2]]
c2=Counter()
for pid,cur,club,kinds in withclub:
    r=reg[pid]
    if cur and club_name(cur,'2005-06')==club: c2['rename']+=1; continue
    allm = sorted(mv4.get(r.get('bbr_id'),[])+mv.get(r.get('bbr_id'),[]), key=lambda m:m['date'])
    c2[allm[-1]['kind'] if allm else 'none']+=1
print('current team != holder, holder has a club:', len(withclub), c2)
print([w for w in withclub if not (mv4.get(reg[w[0]].get('bbr_id')) or mv.get(reg[w[0]].get('bbr_id'))) and not (w[1] and club_name(w[1],'2005-06')==w[2])])
