"""Independent collection of Miami's closed regular-season and playoff results (read-only)."""
import json, re, calendar
from pathlib import Path

ROOT = Path('/home/user/stone-basketball-career')
CAREER = ROOT / 'career/Dwyane_Wade'
MIAMI = 'Miami Heat'
SEASONS = ['2003-04', '2004-05', '2005-06']
CLOCK = '2006-06-20'


def meta(path):
    text = path.read_text(encoding='utf-8')
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                out[k.strip()] = v.strip()
    return out


def games(season, folder='06_Regular_Season'):
    rows = []
    base = CAREER / season / folder
    for p in sorted(base.rglob('Game_*.md')):
        if not re.fullmatch(r'Game_\d+\.md', p.name):
            continue
        m = meta(p)
        rows.append((p, m))
    return rows


def closed(season, folder='06_Regular_Season', game_type='regular'):
    out = []
    problems = []
    for p, m in games(season, folder):
        if m.get('status') != 'played':
            if m.get('status') not in ('not_played',):
                problems.append(f'{p}: status {m.get("status")}')
            continue
        rf = m.get('result_file')
        if not rf or not (p.parent / rf).is_file():
            problems.append(f'{p}: played without result')
            continue
        r = json.loads((p.parent / rf).read_text())
        if r.get('game_type') != game_type or not r.get('terminated') or r['game_date'] > CLOCK:
            problems.append(f'{p}: type {r.get("game_type")} term {r.get("terminated")} date {r["game_date"]}')
            continue
        if r['game_date'] != m.get('date'):
            problems.append(f'{p}: date mismatch note {m.get("date")} result {r["game_date"]}')
        side = 'home' if r['home'] == MIAMI else 'away' if r['away'] == MIAMI else None
        if side is None:
            problems.append(f'{p}: Miami not in result')
            continue
        out.append(dict(note=p, meta=m, result=r, side=side))
    return out, problems


def scope_of_page(page, season):
    parts = page.parts
    month = next((x for x in parts if re.fullmatch(r'\d{2}_[A-Za-z]+', x)), None)
    if not month:
        return f'{season[:4]}-06-01', f'{int(season[:4])+1}-06-30'
    num = int(month[:2]); year = int(season[:4]) + (num < 7)
    last = calendar.monthrange(year, num)[1]
    week = next((int(x[5:]) for x in parts if re.fullmatch(r'Week_\d', x)), None)
    if not week:
        return f'{year}-{num:02d}-01', f'{year}-{num:02d}-{last:02d}'
    s = 1 + (week - 1) * 7
    e = week * 7 if week < 4 else last
    return f'{year}-{num:02d}-{s:02d}', f'{year}-{num:02d}-{e:02d}'


def agg(lines):
    """lines: list of player stat dicts (appearances only)."""
    t = dict(g=0, gs=0, gs_known=True, sec=0.0)
    for k in ('pts', 'fgm', 'fga', 'tpm', 'tpa', 'ftm', 'fta', 'orb', 'drb', 'ast', 'stl', 'blk', 'tov', 'pf'):
        t[k] = 0
    for r in lines:
        t['g'] += 1
        if 'started' in r:
            t['gs'] += 1 if r['started'] else 0
        else:
            t['gs_known'] = False
        t['sec'] += r.get('seconds', (r.get('minutes') or 0) * 60)
        for k in ('pts', 'fgm', 'fga', 'tpm', 'tpa', 'ftm', 'fta', 'orb', 'drb', 'ast', 'stl', 'blk', 'tov', 'pf'):
            t[k] += r.get(k, 0) or 0
    return t


def appeared(r):
    if r.get('appeared') is not None:
        return bool(r['appeared'])
    sec = r.get('seconds')
    if sec is None:
        sec = (r.get('minutes') or 0) * 60
    return sec > 0 or any((r.get(k) or 0) for k in ('pts', 'fga', 'fta', 'orb', 'drb', 'ast', 'stl', 'blk', 'tov', 'pf'))
