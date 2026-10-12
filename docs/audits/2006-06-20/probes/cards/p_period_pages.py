import sys, json, re, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime.league_cards import periods, _read
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
L = ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League'
cards = pickle.load(open('cards.pkl','rb'))
config = _read(ROOT, 'foundation/season_structure.json')
pers = periods(config, '2005-06', ROOT)
def page_rows(path):
    out = {}
    for line in path.read_text(encoding='utf-8').split('\n'):
        m = re.match(r'^\| \[([^\]]+)\]\((?:\.\./)+Players/([^)]+)\.md\) \|(.*)$', line)
        if m:
            out[m.group(2)] = [c.strip() for c in m.group(3).strip().strip('|').split('|')]
    return out
age = collections.Counter(); stat = collections.Counter(); club = collections.Counter(); ex_age = []; ex_stat = []
pages = {}
for per in pers:
    pg = L / per['folder'] / 'League_Stats.md'
    if not pg.is_file(): print('missing page', pg); continue
    pages[per['id']] = page_rows(pg)
for rid, c in cards.items():
    for heading, kind in (('### Season','season'),('### Month','month'),('### Week','week')):
        t = next(t for t in c['tables'] if t[0] == heading)
        ps = [x for x in pers if x['kind'] == kind]
        assert len(ps) == len(t[2]), (rid, kind)
        for per, row in zip(ps, t[2]):
            pr = pages.get(per['id'], {}).get(rid)
            if pr is None: stat['missing on page'] += 1; continue
            if row[5:-1] != pr[4:]:
                stat[kind] += 1
                if len(ex_stat) < 5: ex_stat.append((rid, per['label'], row[5:12], pr[4:11]))
            if row[1] != pr[0]:
                age[kind] += 1
                if len(ex_age) < 5: ex_age.append((rid, per['label'], 'card', row[1], 'page', pr[0]))
            if row[2] != pr[1]: club[kind] += 1
print('stat mismatches', dict(stat), ex_stat)
print('age mismatches', dict(age), 'players', len({e for e in []}))
for e in ex_age: print('  ', e)
print('club cell mismatches', dict(club))
# count players with age mismatch
pl = set()
for rid, c in cards.items():
    for heading, kind in (('### Month','month'),('### Week','week')):
        t = next(t for t in c['tables'] if t[0] == heading)
        for per, row in zip([x for x in pers if x['kind']==kind], t[2]):
            pr = pages[per['id']].get(rid)
            if pr and row[1] != pr[0]: pl.add(rid)
print('players with an age mismatch', len(pl))
