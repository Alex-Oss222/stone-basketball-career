import sys, json, re, pickle, os
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
ROOT = Path('/home/user/stone-basketball-career')
os.chdir(ROOT)
from runtime import write_back
cache = Path('/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/verify-cards-contracts/lines_2005.pkl')
if cache.exists():
    lines = pickle.load(open(cache, 'rb'))
else:
    lines, unmatched = write_back.closed_lines(ROOT, '2005-06', '2006-06-20')
    pickle.dump(lines, open(cache, 'wb'))
reg = json.load(open('career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']
# club full name -> code mapping from card cells: build from cards of players whose club is unique
from collections import Counter, defaultdict
CARDS = ROOT/'career/Dwyane_Wade/Stats_and_Awards/League/Players'
rowre = re.compile(r'^\| \[([^\]]+)\]\(\.\./2005-06/([^)]*)League_Stats\.md\) \| ([^|]*) \| ([^|]*) \| NBA \|')
# period scopes from folder
import calendar
MON = {'11_November':(2005,11),'12_December':(2005,12),'01_January':(2006,1),'02_February':(2006,2),'03_March':(2006,3),'04_April':(2006,4)}
def scope(folder):
    if folder == '':
        return ('2005-10-01','2006-04-30')
    parts = folder.strip('/').split('/')
    y,m = MON[parts[0]]
    if len(parts)==1:
        return (f'{y}-{m:02d}-01', f'{y}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}')
    return None
# week scopes from week page header
def wscope(folder):
    p = ROOT/'career/Dwyane_Wade/Stats_and_Awards/League/2005-06'/folder/'League_Stats.md'
    t = p.read_text()
    m = re.search(r'NBA regular season · (.*)', t)
    return m.group(1)
# build code map: team full name -> code from registry where possible
code_of = {}
for p in reg:
    if p.get('team_name') and p.get('team_code'):
        code_of.setdefault(p['team_name'], p['team_code'])
mismatch = Counter(); cards_aff=set(); examples=[]
for p in reg:
    pid = p['registry_id']
    f = CARDS/f'{pid}.md'
    text = f.read_text()
    recs = [r for r in lines.get(pid, []) if r.get('line') and r['line'].get('appeared')]
    for line in text.splitlines():
        m = rowre.match(line)
        if not m: continue
        label, folder, age, team = m.groups()
        if 'week' in label:
            # derive dates from label e.g. 'November 2005 week 1 (01 to 07)'
            mm = re.match(r'(\w+) (\d{4}) week \d+ \((\d+) to (\d+)\)', label)
            mon = {'November':11,'December':12,'January':1,'February':2,'March':3,'April':4,'October':10}[mm.group(1)]
            y = int(mm.group(2))
            sc = (f'{y}-{mon:02d}-{int(mm.group(3)):02d}', f'{y}-{mon:02d}-{int(mm.group(4)):02d}')
            kind='week'
        elif label.startswith('2005-06'):
            sc = ('2005-10-01','2006-04-30'); kind='season'
        else:
            mm = re.match(r'(\w+) (\d{4})', label)
            mon = {'November':11,'December':12,'January':1,'February':2,'March':3,'April':4,'October':10}[mm.group(1)]
            y=int(mm.group(2))
            start = f'{y}-{mon:02d}-01'
            if mon==11: start='2005-10-01'
            sc = (start, f'{y}-{mon:02d}-{calendar.monthrange(y,mon)[1]:02d}'); kind='month'
        clubs = sorted({r['team'] for r in recs if sc[0] <= r['date'] <= sc[1]})
        if not clubs: continue
        codes = [code_of.get(c, c) for c in clubs]
        if team.strip() not in codes or len(codes)>1:
            mismatch[kind]+=1; cards_aff.add(pid)
            if len(examples)<15: examples.append((pid,label,team,clubs))
print(mismatch, sum(mismatch.values()), len(cards_aff))
for e in examples: print(e)
