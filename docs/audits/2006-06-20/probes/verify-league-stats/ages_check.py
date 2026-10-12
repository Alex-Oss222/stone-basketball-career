"""Age cells on every League_Stats.md vs registry birth date at (a) min(period end, clock) and (b) the caption's 2003-06-26."""
import sys, re, glob, json
from datetime import date
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime.write_back import scope_for
ROOT = '/home/user/stone-basketball-career/career/Dwyane_Wade/Stats_and_Awards/League'
CLOCK = json.load(open('/home/user/stone-basketball-career/career/Dwyane_Wade/2005-06/current_state.json')).get('date') if False else '2006-06-20'
reg = {p['name']: p for p in json.load(open(f'{ROOT}/player_registry.json'))['players']}
def age(b, on):
    b, on = date.fromisoformat(b), date.fromisoformat(on)
    return on.year - b.year - ((on.month, on.day) < (b.month, b.day))
from pathlib import Path
tot = mm_cut = mm_cap = 0; ex = []
for pg in sorted(glob.glob(f'{ROOT}/*/**/League_Stats.md', recursive=True)):
    sc = scope_for(Path(pg), [], CLOCK)
    on = min(sc['end'], CLOCK)
    for l in open(pg):
        m = re.match(r'\| \[([^\]]+)\]\([^)]*\) \| ([^|]+) \|', l)
        if not m: continue
        name, a = m.group(1), m.group(2).strip()
        if name not in reg: continue
        b = reg[name].get('birth_date')
        if not b or a == 'N/A': continue
        tot += 1
        if int(a) != age(b, on): mm_cut += 1; ex.append((pg, name, a, age(b, on)))
        if int(a) != age(b, '2003-06-26'): mm_cap += 1
print('age cells', tot, 'mismatch vs min(end,clock)', mm_cut, 'mismatch vs caption 2003-06-26', mm_cap)
print(ex[:5])
p = f'{ROOT}/2005-06/League_Stats.md'
for n in ('Alvin Williams', 'Dwyane Wade'):
    print(n, reg[n]['birth_date'], age(reg[n]['birth_date'], '2006-06-20'), age(reg[n]['birth_date'], '2003-06-26'))
