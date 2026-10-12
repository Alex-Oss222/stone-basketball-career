"""Production totals, per-36, shooting, efficiency and game highs on every detail block vs independent recomputation."""
import re
from pathlib import Path
from compare import games, scope_from_path, CAREER, agg, n, STATS

def section(text, head):
    if f'### {head}\n' not in text: return None
    s = text.split(f'### {head}\n', 1)[1]
    return s.split('\n### ', 1)[0]

def rows(sec):
    return [[c.strip() for c in l.strip().strip('|').split(' | ')] for l in sec.splitlines() if l.startswith('| ') and not l.startswith('| ---')][1:]

def pct(v): return 'N/A' if v is None else f'{100*v:.1f}%'
problems = []; checked = 0
for page in sorted(CAREER.rglob('*.md')):
    rel = page.relative_to(CAREER)
    if 'League' in rel.parts or (len(rel.parts) > 1 and rel.parts[1] == 'Team'): continue
    text = page.read_text()
    prod = section(text, 'Production')
    if prod is None: continue
    if 'National_Team' in rel.parts: continue
    sc = scope_from_path(page)
    if sc is None: problems.append(('unmapped', str(rel))); continue
    checked += 1
    sel = [g for g in sc['games'] if g['status'] == 'played']
    t = agg(sel)
    if t is None:
        continue
    played = [g['row'] for g in sel if g['cov'] == 'played']
    G = t['g']; mins = t['seconds'] / 60
    keymap = {'PTS': 'pts', 'OREB': 'orb', 'DREB': 'drb', 'AST': 'ast', 'STL': 'stl', 'BLK': 'blk', 'TOV': 'tov', 'PF': 'pf',
              'FGM': 'fgm', 'FGA': 'fga', '3PM': 'tpm', '3PA': 'tpa', 'FTM': 'ftm', 'FTA': 'fta', 'FT points': 'ftm'}
    tot = dict(t); tot['reb'] = t['orb'] + t['drb']; tot['2pm'] = t['fgm'] - t['tpm']; tot['2pa'] = t['fga'] - t['tpa']
    keymap.update({'REB': 'reb', '2PM': '2pm', '2PA': '2pa'})
    for r in rows(prod):
        m, total, perapp, per36 = r
        if m == 'MIN':
            exp = [n(mins), n(mins / G if G else None), '36.0' if mins else 'N/A']
        else:
            v = tot[keymap[m]]
            exp = [n(v, 0), n(v / G if G else None), n(v * 36 / mins if mins else None)]
        if [total, perapp, per36] != exp: problems.append(('prod', str(rel), m, [total, perapp, per36], exp))
    shoot = section(text, 'Shooting')
    for r in rows(shoot):
        lab, mk, at, p = r
        mm, aa = {'All field goals': ('fgm', 'fga'), 'Two-pointers': ('2pm', '2pa'), 'Three-pointers': ('tpm', 'tpa'), 'Free throws': ('ftm', 'fta')}[lab]
        exp = [n(tot[mm], 0), n(tot[aa], 0), pct(tot[mm] / tot[aa] if tot[aa] else None)]
        if [mk, at, p] != exp: problems.append(('shoot', str(rel), lab, [mk, at, p], exp))
    eff = section(text, 'Efficiency and shot selection')
    dd = td = 0
    for r in played:
        c = sum(r[k] >= 10 for k in ('pts', 'stl', 'blk', 'ast')) + ((r['orb'] + r['drb']) >= 10)
        dd += c >= 2; td += c >= 3
    expect = {'eFG%': pct((t['fgm'] + .5 * t['tpm']) / t['fga'] if t['fga'] else None),
              'TS% (estimated)': pct(t['pts'] / (2 * (t['fga'] + .44 * t['fta'])) if (t['fga'] or t['fta']) else None),
              'Three-point attempt share': pct(t['tpa'] / t['fga'] if t['fga'] else None),
              'Free-throw attempt rate': n(t['fta'] / t['fga'] if t['fga'] else None, 3),
              'Assist / turnover ratio': n(t['ast'] / t['tov'] if t['tov'] else None, 2),
              'Plus/minus total': 'N/A',
              'Double-doubles': n(dd, 0), 'Triple-doubles': n(td, 0)}
    for r in rows(eff):
        if r[1] != expect[r[0]]: problems.append(('eff', str(rel), r[0], r[1], expect[r[0]]))
    highs = section(text, 'Game highs')
    for r in rows(highs):
        k = {'PTS': 'pts', 'REB': 'reb', 'AST': 'ast', 'STL': 'stl', 'BLK': 'blk', 'TOV': 'tov'}[r[0]]
        vals = [(g, (g['row']['orb'] + g['row']['drb']) if k == 'reb' else g['row'][k]) for g in sel if g['cov'] == 'played']
        if not vals:
            if r[1] != 'N/A': problems.append(('high-empty', str(rel), r))
            continue
        hi = max(v for _, v in vals)
        ties = sorted(g['date'] for g, v in vals if v == hi)
        shown_dates = sorted(re.findall(r'\[(\d{4}-\d{2}-\d{2})', r[2]))
        if r[1] != str(hi) or shown_dates != ties: problems.append(('high', str(rel), r[0], r[1], hi, shown_dates, ties))
print('checked', checked, 'problems', len(problems))
for p in problems[:40]: print(p)
