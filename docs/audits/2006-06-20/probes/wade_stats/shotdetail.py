"""Every 'Game shooting detail' and 'Game log' row vs the game's own box."""
import re
from compare import games, CAREER, pages
idx = {g['path']: g for g in games}
def pct(v): return 'N/A' if v is None else f'{100*v:.1f}%'
bad = 0; n = 0
for p in pages():
    t = p.read_text()
    for sec_name in ('### Game shooting detail', '### Game log'):
        if sec_name not in t: continue
        for sec in t.split(sec_name)[1:]:
            body = sec.split('\n###', 1)[0]
            for line in body.splitlines():
                m = re.match(r'\| \[(\d{4}-\d{2}-\d{2})\]\(([^)]+)\) \| (.*) \|$', line)
                if not m: continue
                g = idx[(p.parent / m.group(2)).resolve()]
                c = [x.strip() for x in m.group(3).split(' | ')]
                n += 1
                if g['cov'] != 'played':
                    continue
                r = g['row']
                if sec_name == '### Game shooting detail':
                    exp = [f"{r['fgm']}/{r['fga']}", f"{r['fgm']-r['tpm']}/{r['fga']-r['tpa']}", f"{r['tpm']}/{r['tpa']}", f"{r['ftm']}/{r['fta']}",
                           pct((r['fgm'] + .5*r['tpm'])/r['fga'] if r['fga'] else None), pct(r['pts']/(2*(r['fga']+.44*r['fta'])) if (r['fga'] or r['fta']) else None), 'N/A', str(r['pf'])]
                else:
                    exp = [g['meta']['opponent'], g['meta']['venue'], g['meta']['result'], 'Played', f"{r['seconds']/60:.1f}", str(r['pts']), str(r['orb']+r['drb']), str(r['ast']), str(r['stl']), str(r['blk']), str(r['tov'])]
                if c != exp:
                    bad += 1
                    if bad < 10: print(p.relative_to(CAREER), m.group(1), c, exp)
print('rows', n, 'bad', bad)
