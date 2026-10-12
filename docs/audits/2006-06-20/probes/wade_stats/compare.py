"""Parse every Wade per-game table row and compare to an independent recomputation from closed results."""
import json, os, re, sys, calendar
from datetime import date
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from collect import collect, appeared, STATS, CAREER, REPO

CLOCK = '2006-06-20'
BIRTH = date(1984, 1, 17)
def age_on(d):
    d = date.fromisoformat(d)
    return d.year - BIRTH.year - ((d.month, d.day) < (BIRTH.month, BIRTH.day))

games, issues = collect()
# injured list coverage
IL = {}
for s in ('2003-04', '2004-05', '2005-06'):
    p = CAREER / s / '00_Team/Transactions/injured_list.json'
    IL[s] = [e for e in json.loads(p.read_text())['entries'] if e['player'] == 'Dwyane Wade']
def covered_dnp(g):
    if g.get('inactive'): return True
    for e in IL[g['season']]:
        if e['placed'] <= g['game_date'] and (e.get('activated') is None or g['game_date'] < e['activated']):
            return True
    return False

KIND = {'05_Preseason': 'preseason', '06_Regular_Season': 'regular', '08_Playoffs': 'playoff'}
for g in games:
    if g['phase'] == '11_All_Star':
        g['comp'] = g['game_type']
    else:
        g['comp'] = KIND[g['phase']]
    g['date'] = g['meta']['date']
    g['path'] = (CAREER / g['note']).resolve()
    if g['status'] == 'played':
        if g['row'] is not None:
            g['cov'] = 'played' if appeared(g['row']) else 'dnp'
        else:
            g['cov'] = 'dnp' if covered_dnp(g) else 'missing'

def agg(sel):
    sel = [g for g in sel if g['status'] == 'played']
    if any(g['cov'] == 'missing' for g in sel):
        return None
    rows = [g['row'] for g in sel if g['cov'] == 'played']
    t = {k: sum(r[k] for r in rows) for k in STATS}
    t['g'] = len(rows); t['gs'] = sum(1 for r in rows if r.get('started'))
    return t

def n(v, p=1): return 'N/A' if v is None else f'{v:.{p}f}'
def sh(v): return 'N/A' if v is None else f'{v:.3f}'.removeprefix('0')
def expected_cells(t):
    if t is None:
        return ['N/A'] * 26
    g = t['g']
    r = lambda a, b: a / b if b else None
    pg = lambda k: r(t[k], g)
    two_m = t['fgm'] - t['tpm']; two_a = t['fga'] - t['tpa']
    return [n(g, 0), n(t['gs'], 0) if g else 'N/A', n(r(t['seconds'] / 60, g)), n(pg('fgm')), n(pg('fga')), sh(r(t['fgm'], t['fga'])),
            n(pg('tpm')), n(pg('tpa')), sh(r(t['tpm'], t['tpa'])), n(r(two_m, g)), n(r(two_a, g)), sh(r(two_m, two_a)),
            sh(r(t['fgm'] + .5 * t['tpm'], t['fga'])), n(pg('ftm')), n(pg('fta')), sh(r(t['ftm'], t['fta'])),
            n(pg('orb')), n(pg('drb')), n(r(t['orb'] + t['drb'], g)), n(pg('ast')), n(pg('stl')), n(pg('blk')), n(pg('tov')), n(pg('pf')), n(pg('pts')),
            sh(r(t['pts'], 2 * (t['fga'] + .44 * t['fta'])))]

MONTHS = {m: i for i, m in enumerate(calendar.month_name) if m}
def season_of(parts):
    return next((p for p in parts if re.fullmatch(r'\d{4}-\d{2}', p)), None)

def scope_from_path(path):
    """Independent: the set of games and period end a page/target path represents."""
    path = Path(path).resolve()
    rel = path.relative_to(CAREER.resolve())
    parts = rel.parts
    season = season_of(parts)
    if path.name.startswith('Game_') and path.suffix == '.md':
        gs = [g for g in games if g['path'] == path]
        return dict(games=gs, end=gs[0]['date'], kind='game', season=season)
    if season is None:
        return None
    if parts[0] == 'Stats_and_Awards' or (len(parts) > 1 and parts[1] == '06_Regular_Season'):
        reg = [g for g in games if g['season'] == season and g['comp'] == 'regular']
        mfold = next((p for p in parts if re.fullmatch(r'\d{2}_[A-Za-z]+', p)), None)
        if mfold is None:
            last = max(g['date'] for g in reg)
            return dict(games=reg, end=last, kind='season_regular', season=season)
        num = int(mfold[:2]); year = int(season[:4]) + (num < 7)
        lastday = calendar.monthrange(year, num)[1]
        lo, hi = f'{year}-{num:02d}-01', f'{year}-{num:02d}-{lastday:02d}'
        wk = next((int(p[5:]) for p in parts if re.fullmatch(r'Week_\d', p)), None)
        if wk:
            lo = f'{year}-{num:02d}-{1 + (wk - 1) * 7:02d}'
            hi = f'{year}-{num:02d}-{wk * 7:02d}' if wk < 4 else hi
        gs = [g for g in reg if lo <= g['date'] <= hi]
        return dict(games=gs, end=min(hi, CLOCK), start=lo, kind='week' if wk else 'month', season=season, month_start=f'{year}-{num:02d}-01')
    phase = parts[1]
    if phase == '05_Preseason':
        gs = [g for g in games if g['season'] == season and g['comp'] == 'preseason']
        return dict(games=gs, end=max(g['date'] for g in gs), kind='preseason', season=season)
    if phase == '08_Playoffs':
        gs = [g for g in games if g['season'] == season and g['comp'] == 'playoff']
        if len(parts) > 3:
            gs = [g for g in gs if g['note'].split('/')[2] == parts[2]]
            kind = 'round'
        else:
            kind = 'playoffs'
        return dict(games=gs, end=max((g['date'] for g in gs), default=None), kind=kind, season=season)
    if phase == '11_All_Star':
        if len(parts) > 3:
            comp = {'Rookie_Challenge': 'rookie_challenge', 'All_Star_Game': 'all_star'}[parts[2]]
            gs = [g for g in games if g['season'] == season and g['comp'] == comp]
        else:
            gs = [g for g in games if g['season'] == season and g['comp'] in ('rookie_challenge', 'all_star')]
        return dict(games=gs, end=max((g['date'] for g in gs), default=None), kind='allstar', season=season)
    if phase == '02_Summer_League':
        return dict(games=[], end=None, kind='summer', season=season)
    if phase in ('07_Play_In_Tournament',):
        return dict(games=[], end=None, kind='playin', season=season)
    return None

def parse_tables(text):
    out = []
    heading = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        L = lines[i]
        if L.startswith('#'):
            heading = L.lstrip('#').strip()
        if L.startswith('| Scope | Age | Team | Lg | Pos | G | GS | MP |'):
            i += 2
            while i < len(lines) and lines[i].startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split(' | ')]
                out.append((heading, cells, i + 1))
                i += 1
            continue
        i += 1
    return out

LINK = re.compile(r'^\[([^\]]+)\]\(([^)]+)\)$')
def row_scope(page, page_scope, heading, label):
    m = LINK.match(label)
    if m:
        lab, href = m.groups()
        target = (page.parent / href.split('#')[0].split('?')[0]).resolve()
        if heading and ('NBA regular season' == heading or 'NBA playoffs' == heading or 'exhibition' in heading) and page.name == 'README.md' and season_of(page.relative_to(CAREER).parts) is None:
            sc = scope_from_path(target)
            # career README season rows
            if heading == 'NBA regular season':
                gs = [g for g in games if g['season'] == lab and g['comp'] == 'regular']
            elif heading == 'NBA playoffs':
                gs = [g for g in games if g['season'] == lab and g['comp'] == 'playoff']
            else:
                comp = 'rookie_challenge' if heading.startswith('Rookie') else 'all_star'
                gs = [g for g in games if g['season'] == lab and g['comp'] == comp]
            return dict(games=gs, end=min(CLOCK, f'{int(lab[:4]) + 1}-06-30'), kind='career_season')
        sc = scope_from_path(target)
        if sc is None:
            return None
        return sc
    if label == 'Career total':
        comp = {'NBA regular season': 'regular', 'NBA playoffs': 'playoff'}.get(heading)
        if comp is None:
            comp = 'rookie_challenge' if heading.startswith('Rookie') else 'all_star'
        return dict(games=[g for g in games if g['comp'] == comp], end=CLOCK)
    if 'National_Team' in str(page):
        return dict(games=[], end=CLOCK)
    base = page_scope
    if base is None:
        return None
    gs = base['games']
    if label in ('This scope', 'This game', 'This week') or re.fullmatch(r'[A-Z][a-z]+ \d{4}', label):
        return base
    if label in ('Home', 'Away', 'Neutral'):
        return dict(base, games=[g for g in gs if g['status'] == 'played' and g['meta']['venue'] == label.lower()])
    if label in ('Wins', 'Losses'):
        return dict(base, games=[g for g in gs if g['status'] == 'played' and g['meta']['result'][0] == label[0]])
    if label.startswith('Team: '):
        return dict(base, games=[g for g in gs if g['status'] == 'played' and g['meta'].get('player_team') == label[6:]])
    if label == 'Month through this week':
        reg = [g for g in games if g['season'] == base['season'] and g['comp'] == 'regular']
        return dict(games=[g for g in reg if base['month_start'] <= g['date'] <= base['end']], end=base['end'])
    if label in ('Season through this week', 'Season through this month'):
        reg = [g for g in games if g['season'] == base['season'] and g['comp'] == 'regular']
        return dict(games=[g for g in reg if g['date'] <= base['end']], end=base['end'])
    if label == 'Career total':
        comp = {'NBA regular season': 'regular', 'NBA playoffs': 'playoff'}.get(heading)
        if comp is None:
            comp = 'rookie_challenge' if heading.startswith('Rookie') else 'all_star'
        return dict(games=[g for g in games if g['comp'] == comp], end=CLOCK)
    return None

def pages():
    out = []
    for p in sorted(CAREER.rglob('*.md')):
        rel = p.relative_to(CAREER)
        if rel.parts[0] in ('Stats_and_Awards',):
            if len(rel.parts) > 1 and rel.parts[1] in ('League', 'Team'):
                continue
        elif re.fullmatch(r'\d{4}-\d{2}', rel.parts[0]):
            if len(rel.parts) < 2 or rel.parts[1] not in ('02_Summer_League', '05_Preseason', '06_Regular_Season', '07_Play_In_Tournament', '08_Playoffs', '11_All_Star', 'README.md'):
                continue
        elif rel.parts[0] not in ('README.md', 'National_Team'):
            continue
        out.append(p)
    return out

if __name__ == '__main__':
    bad = []; nrows = 0; npages = 0; unmapped = []
    agediff = []
    for page in pages():
        text = page.read_text()
        rows = parse_tables(text)
        if not rows: continue
        npages += 1
        rel = page.relative_to(CAREER)
        try:
            ps = scope_from_path(page) if page.name != 'README.md' or len(rel.parts) > 1 else None
        except Exception as e:
            ps = None
        if rel.parts[0] == 'Stats_and_Awards' and len(rel.parts) == 2:
            ps = None
        if len(rel.parts) == 2 and re.fullmatch(r'\d{4}-\d{2}', rel.parts[0]) and rel.parts[1] == 'README.md':
            ps = None
        for heading, cells, ln in rows:
            nrows += 1
            label = cells[0]
            if heading == 'Individual game boxes':
                m = LINK.match(label)
                sc = scope_from_path((page.parent / m.group(2)).resolve())
            else:
                sc = row_scope(page, ps, heading, label)
            if sc is None:
                unmapped.append((str(rel), ln, heading, label)); continue
            if sc.get('kind') == 'game' and heading not in ('Individual game boxes',) and not label.startswith('['):
                pass
            exp = expected_cells(agg(sc['games']))
            shown = cells[5:31]
            if exp != shown:
                diffs = [(i, a, b) for i, (a, b) in enumerate(zip(shown, exp)) if a != b]
                bad.append((str(rel), ln, heading, label, diffs))
            # age
            dates = sorted(g['date'] for g in sc['games'] if g['status'] == 'played')
            ages = {age_on(d) for d in dates}
            agediff.append((str(rel), ln, heading, label, cells[1], sorted(ages), sc.get('end'), cells[2], cells[3], cells[4]))
    print('pages', npages, 'rows', nrows, 'unmapped', len(unmapped), 'mismatched', len(bad))
    for u in unmapped[:40]: print('UNMAPPED', u)
    COLS = ['G','GS','MP','FG','FGA','FG%','3P','3PA','3P%','2P','2PA','2P%','eFG%','FT','FTA','FT%','ORB','DRB','TRB','AST','STL','BLK','TOV','PF','PTS','TS%']
    for b in bad[:200]:
        print('MISMATCH', b[0], b[1], b[2], b[3][:60], [(COLS[i], a, e) for i, a, e in b[4]])
    json.dump(agediff, open(os.path.join(os.path.dirname(__file__), 'ages.json'), 'w'))
