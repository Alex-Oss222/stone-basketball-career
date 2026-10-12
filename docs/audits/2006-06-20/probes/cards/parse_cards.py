import sys, json, re, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
CARDS = ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League/Players'
reg = json.load(open(ROOT / 'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']

def tables(text):
    """list of (heading, header, rows)"""
    out = []
    heading = None
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith('#'):
            heading = l
        if l.startswith('| ') and i + 1 < len(lines) and lines[i+1].startswith('| ---'):
            header = [c.strip() for c in l.strip().strip('|').split('|')]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].startswith('|'):
                rows.append([c.strip() for c in lines[j].strip().strip('|').split('|')])
                j += 1
            out.append((heading, header, rows))
            i = j
            continue
        i += 1
    return out

cards = {}
missing = []
for p in reg:
    rid = p['registry_id']
    md = CARDS / f'{rid}.md'
    html = CARDS / f'{rid}.html'
    if not md.is_file() or not html.is_file():
        missing.append((rid, md.is_file(), html.is_file()))
        continue
    t = md.read_text(encoding='utf-8')
    m = re.search(r'\*\*Card date:\*\* (\S+) · \*\*Club on this date:\*\* (.*?) · \*\*Basis:\*\* (.*?) · \*\*League', t)
    j = re.search(r'\*\*Jersey:\*\* (#\S+|Unassigned)', t)
    a = re.search(r'\*\*Age on card date:\*\* (\S+)', t)
    heads = [l for l in t.split('\n') if l.startswith('## ')]
    cards[rid] = dict(text=t, date=m.group(1) if m else None, label=m.group(2) if m else None, basis=m.group(3) if m else None,
                      jersey=j.group(1) if j else None, age=a.group(1) if a else None, heads=heads, tables=tables(t))
print('registry', len(reg), 'cards parsed', len(cards), 'missing', missing)
pickle.dump(cards, open('cards.pkl', 'wb'))
# section order
bad = []
for rid, c in cards.items():
    h = c['heads']
    if h[-3:] != ['## Regular-season statistics by year', '## Playoff statistics by year', '## Awards and honors']:
        bad.append((rid, h[-3:]))
print('section order bad', len(bad), bad[:5])
