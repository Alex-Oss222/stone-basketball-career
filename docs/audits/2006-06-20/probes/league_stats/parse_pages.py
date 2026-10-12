"""Parse League_Stats.md pages into {group: [row dicts]}."""
import re, json, sys
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
LEAGUE = ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League'

def parse(page):
    text = Path(page).read_text()
    groups = {}
    for m in re.finditer(r"<details>\n<summary>(PG|SG|SF|F|PF|C) · ([^\n]*)</summary>\n(.*?)</details>", text, re.S):
        pos, summ, body = m.groups()
        rows = []
        lines = [l for l in body.splitlines() if l.startswith('|')]
        if not lines:
            groups[pos] = dict(summary=summ, rows=[]); continue
        headers = [c.strip() for c in lines[0].strip().strip('|').split('|')]
        for l in lines[2:]:
            cells = [c.strip() for c in l.strip().strip('|').split('|')]
            d = dict(zip(headers, cells))
            mm = re.match(r"^\[([^\]]+)\]\(([^)]+)\)$", d['Player'])
            d['name'] = mm.group(1) if mm else d['Player']
            d['href'] = mm.group(2) if mm else None
            rows.append(d)
        groups[pos] = dict(summary=summ, rows=rows, headers=headers)
    return text, groups

if __name__ == '__main__':
    text, g = parse(sys.argv[1])
    for pos, d in g.items():
        print(pos, d['summary'], len(d['rows']))
