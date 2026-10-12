"""Miami personnel cards (career/Dwyane_Wade/<season>/00_Team/Team/Player_Cards/*.md) against closed results:
regular-season rows for Miami seasons, playoff sections, coverage lines and ages."""
import sys, re, json
from datetime import date
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent))
from collect import *

# Miami lines per season, regular and playoff
reg = {}
po = {}
for s in SEASONS:
    g, p = closed(s)
    reg[s] = g
    gp, pp = closed(s, '08_Playoffs', 'playoff')
    po[s] = gp
    if pp:
        print('playoff problems', s, pp[:5])


def lines_for(games, name):
    out = []
    for g in games:
        for r in g['result']['player_stats'][g['side']]:
            if r['player_id'] == name and appeared(r):
                out.append(r)
    return out


def pct(m, a):
    return f"{100*m/a:.1f}%" if a else 'N/A'


def row_expect(lines):
    a = agg(lines)
    g = a['g']
    if not g:
        return None
    return [str(g), str(a['gs']), f"{a['sec']/60/g:.1f}", f"{a['pts']/g:.1f}", f"{(a['orb']+a['drb'])/g:.1f}",
            f"{a['ast']/g:.1f}", f"{a['stl']/g:.1f}", f"{a['blk']/g:.1f}", f"{a['tov']/g:.1f}",
            (a['fgm'], a['fga']), (a['tpm'], a['tpa']), (a['ftm'], a['fta'])]


def pct_match(cell, ma):
    m, a = ma
    if not a:
        return cell in ('N/A', '')
    v = m / a
    c = cell.strip()
    if c.endswith('%'):
        return abs(float(c[:-1]) - 100 * v) < 0.051
    try:
        return abs(float(c) - v) < 0.00051
    except ValueError:
        return False


def section(text, head, nxt):
    i = text.find(head)
    if i < 0:
        return ''
    j = text.find(nxt, i + len(head))
    return text[i:j if j > 0 else None]


issues = defaultdict(list)
for season in SEASONS:
    folder = CAREER / season / '00_Team/Team/Player_Cards'
    roster = json.loads((CAREER / season / '00_Team/Team/Roster/roster.json').read_text())
    births = {p['name']: p.get('date_of_birth') for p in roster['players']}
    for card in sorted(folder.glob('*.md')):
        if card.name == 'TEMPLATE.md':
            continue
        text = card.read_text()
        m = re.search(r'^# (.+?) \| (\S+) Player Profile', text, re.M)
        if not m:
            issues['unparsed'].append(str(card)); continue
        name = m.group(1)
        regsec = section(text, '## Regular-season statistics by year', '## Playoff statistics by year')
        posec = section(text, '## Playoff statistics by year', '<!-- yearly-statistics:end -->')
        cov = re.search(r'^\*\*Coverage:\*\* (.*)$', regsec, re.M)
        for s in SEASONS:
            # regular rows
            rows = [l for l in regsec.splitlines() if l.startswith(f'| {s} |')]
            exp = row_expect(lines_for(reg[s], name))
            if rows:
                cells = [c.strip() for c in rows[0].strip().strip('|').split('|')]
                team = cells[1]
                if team in ('MIA', 'Miami Heat'):
                    if exp is None:
                        if cells[2] != '0':
                            issues['reg-row-no-games'].append((str(card.relative_to(CAREER)), s, cells))
                    else:
                        ok = cells[2:11] == exp[:9] and all(pct_match(cells[11 + k], exp[9 + k]) for k in range(3))
                        if not ok:
                            issues['reg-row-mismatch'].append((str(card.relative_to(CAREER)), s, cells[2:], exp))
                elif exp is not None:
                    issues['reg-row-other-team-but-miami-games'].append((str(card.relative_to(CAREER)), s, cells[:4], exp[:2]))
            elif exp is not None and s <= season:
                issues['reg-row-missing'].append((str(card.relative_to(CAREER)), s, exp[:3]))
            # playoff
            pexp = row_expect(lines_for(po[s], name))
            prow = [l for l in posec.splitlines() if l.startswith(f'| {s} |')]
            if s <= season and pexp is not None:
                if not prow:
                    issues['po-missing'].append((str(card.relative_to(CAREER)), s, pexp[:3], posec.strip().splitlines()[2][:110] if len(posec.strip().splitlines()) > 2 else ''))
                else:
                    cells = [c.strip() for c in prow[0].strip().strip('|').split('|')]
                    if cells[2:11] != pexp[:9]:
                        issues['po-mismatch'].append((str(card.relative_to(CAREER)), s, cells[2:6], pexp[:4]))
        if cov and 'not started' in cov.group(1):
            ns = re.findall(r'(\d{4}-\d{2}) not started', cov.group(1))
            for s in ns:
                if s in reg and row_expect(lines_for(reg[s], name)):
                    issues['coverage-not-started-but-played'].append((str(card.relative_to(CAREER)), s, cov.group(1)[:140]))
        # age at assessment
        am = re.search(r'\*\*Age at assessment:\*\* (\S+)', text)
        dm = re.search(r'\*\*Opening assessment:\*\* ([A-Z][a-z]+ \d+, \d{4})', text)
        if am and dm and births.get(name):
            from datetime import datetime
            d = datetime.strptime(dm.group(1), '%B %d, %Y').date()
            b = date.fromisoformat(births[name])
            age = d.year - b.year - ((d.month, d.day) < (b.month, b.day))
            if am.group(1) != str(age):
                issues['age'].append((str(card.relative_to(CAREER)), am.group(1), age, births[name], dm.group(1)))

for k, v in issues.items():
    print('==', k, len(v))
    for x in v:
        print('  ', x)
