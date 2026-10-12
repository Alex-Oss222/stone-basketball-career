"""For every League_Stats.md: header 'N tracked players' and each <summary> count vs the rows the table lists;
alphabetical order breaks per group."""
import re, glob, json
ROOT = '/home/user/stone-basketball-career/career/Dwyane_Wade/Stats_and_Awards/League'
reg = json.load(open(f'{ROOT}/player_registry.json'))
pages = sorted(glob.glob(f'{ROOT}/*/**/League_Stats.md', recursive=True))
print('pages', len(pages), 'registry', reg['player_count'], len(reg['players']))
stale = 0; stale_pages = 0; header_bad = 0
first = True
for pg in pages:
    t = open(pg).read()
    m = re.search(r'^(\d+) tracked players', t, re.M)
    blocks = re.findall(r'<summary>(\S+) · [^·]+ · (\d+) players</summary>\n(.*?)</details>', t, re.S)
    total = 0; bad = 0; breaks = {}
    for pos, n, body in blocks:
        rows = [l for l in body.splitlines() if l.startswith('| [')]
        names = [re.match(r'\| \[([^\]]+)\]', l).group(1) for l in rows]
        total += len(rows)
        if int(n) != len(rows): bad += 1
        breaks[pos] = (int(n), len(rows), sum(1 for a, b in zip(names, names[1:]) if a.casefold() > b.casefold()))
    hb = int(m.group(1)) != total
    header_bad += hb
    stale += bad + hb
    stale_pages += bool(bad or hb)
    if first or pg.endswith('2005-06/League_Stats.md'):
        print(pg.split('League/')[1], 'header', m.group(1), 'rows', total, breaks)
        first = False
print('stale counts', stale, 'pages with stale counts', stale_pages, 'header stale', header_bad)
