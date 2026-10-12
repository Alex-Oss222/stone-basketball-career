import sys, json, re
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
CAREER = ROOT/'career/Dwyane_Wade'
def fm(path):
    t = path.read_text(encoding='utf-8')
    m = re.match(r'---\n(.*?)\n---', t, re.S)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1); out[k.strip()] = v.strip()
    return out
def wade_rows(season, phase):
    rows = []
    for note in sorted((CAREER/season/phase).rglob('Game_*.md')):
        f = fm(note)
        if f.get('status') != 'played' or not f.get('result_file'): 
            rows.append((note, f, None, None)); continue
        res = json.loads((note.parent/f['result_file']).read_text())
        row = None
        for side in ('home', 'away'):
            for p in res['player_stats'][side]:
                if p['player_id'] == 'Dwyane Wade':
                    row = p
        rows.append((note, f, res, row))
    return rows
