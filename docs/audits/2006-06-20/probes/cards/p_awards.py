import sys, json, re, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime.write_back import _key
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
L = ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League'
reg = json.load(open(L/'player_registry.json'))['players']
bykey = {_key(p['name']): p['registry_id'] for p in reg}
bybbr = {p['bbr_id']: p['registry_id'] for p in reg if p.get('bbr_id')}
cards = pickle.load(open('cards.pkl','rb'))
ON = '2006-06-20'
exp = collections.defaultdict(set); unknown = []
def add(name, label, day, bbr=None):
    rid = bybbr.get(bbr) if bbr else None
    rid = rid or bykey.get(_key(name))
    if not rid: unknown.append((name, label, day)); return
    exp[rid].add((label, day))
for s in ('2003-04','2004-05','2005-06'):
    for d in json.load(open(L/s/'award_decisions.json'))['decisions']:
        if d['announced_on'] > ON: continue
        for x in d['shortlist']:
            if x['rank'] == 1:
                add(x['player'], f"{d['conference']} {d['name']}".strip(), d['announced_on'])
    for d in json.load(open(L/s/'season_awards.json'))['decisions']:
        if d['announced_on'] > ON or d['award'] == 'coy': continue
        for w in d.get('winners') or []:
            add(w, d['name'], d['announced_on'])
        for t in d.get('teams', []):
            for p in t['players']:
                add(p['player'], d['name'].replace(' Teams', '') + ' ' + t['team'], d['announced_on'])
    a = L/s/'all_star.json'
    if a.is_file():
        for x in json.load(open(a))['all_stars']:
            if x['selected_on'] <= ON:
                add(x['player'], f"{x['conference']} All-Star ({x['role']})", x['selected_on'], x.get('bbr_id'))
    g = L/s/'all_star_games.json'
    if g.is_file():
        for game in json.load(open(g))['games'].values():
            m = game.get('mvp')
            if m and max(game['date'], m.get('recorded_on') or '') <= ON:
                ids = {p['player']: p['bbr_id'] for t in game['teams'].values() for p in t['players']}
                for w in m['winners']:
                    add(w, m['name'], game['date'], ids.get(w))
got = collections.defaultdict(set); other_rows = collections.Counter()
for rid, c in cards.items():
    t = [t for t in c['tables'] if t[0] == '## Awards and honors']
    if not t: continue
    for row in t[0][2]:
        if row[3] in ('**Winner**', '**Selected**'):
            got[rid].add((row[0], row[2]))
        else: other_rows[re.sub(r'\d', 'N', row[3])] += 1
missing = [(rid, x) for rid in exp for x in exp[rid] - got.get(rid, set())]
extra = [(rid, x) for rid in got for x in got[rid] - exp.get(rid, set())]
print('expected won honors', sum(len(v) for v in exp.values()), 'card won rows', sum(len(v) for v in got.values()))
print('unmatched record names', unknown[:20])
print('missing on cards', len(missing)); [print('  ', m) for m in missing[:30]]
print('extra on cards', len(extra)); [print('  ', m) for m in extra[:30]]
print(other_rows.most_common(20))
