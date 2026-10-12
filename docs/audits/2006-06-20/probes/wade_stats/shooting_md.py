"""Shooting.md headline rows and located-attempt zone counts vs independent recomputation."""
import re
from collections import Counter
from compare import games, CAREER
COMP = {'NBA regular season': 'regular', 'NBA playoffs': 'playoff', 'NBA preseason': 'preseason', 'NBA All-Star Game': 'all_star', 'Rookie Challenge': 'rookie_challenge'}
ZONES = {'paint': 'Paint', 'short_mid': 'Outside paint, under 12 ft'}
text = (CAREER / 'Stats_and_Awards/Shooting.md').read_text()
secs = re.split(r'\n## ', text)[1:]
problems = []; n = 0
import calendar
for sec in secs:
    head = sec.splitlines()[0]
    parts = head.split(' · ')
    comp = COMP.get(parts[-1]) or COMP.get(parts[1] if len(parts) > 1 else '')
    if parts[-1].startswith('through'):
        comp = COMP[parts[1]]; season = parts[0]
        sel = [g for g in games if g['season'] == season and g['comp'] == comp]
        if season == '2006-07': sel = []
    elif re.fullmatch(r'\d{4}-\d{2}-\d{2} to \d{4}-\d{2}-\d{2}', parts[0]):
        lo, hi = parts[0].split(' to ')
        sel = [g for g in games if g['comp'] == comp and lo <= g['date'] <= hi]
    elif re.fullmatch(r'\d{4}-\d{2}', parts[0]):
        sel = [g for g in games if g['comp'] == comp and g['date'][:7] == parts[0]]
    else:
        m = re.match(r'(\d{4}-\d{2}-\d{2}) (at|vs) (.*)', parts[0])
        sel = [g for g in games if g['comp'] == comp and g['date'] == m.group(1) and g['meta']['opponent'] == m.group(3)]
        if len(sel) != 1: problems.append(('game-map', head, len(sel))); continue
    n += 1
    played = [g for g in sel if g['status'] == 'played']
    rows = [l for l in sec.splitlines() if l.startswith('| ') and not l.startswith('| ---')]
    hdr = rows[1].strip('| ').split(' | ')
    app, dnp, closed, fg, fgp, tp, pts, cov = [c.strip() for c in rows[1].strip().strip('|').split('|')]
    missing = any(g['cov'] == 'missing' for g in played)
    ap = [g for g in played if g['cov'] == 'played']
    if missing:
        exp_app = 'N/A'
    else:
        exp_app = str(len(ap))
    t = lambda k: sum(g['row'][k] for g in ap)
    exp = [exp_app, str(sum(1 for g in played if g['cov'] == 'dnp')), str(len(played))]
    if not missing:
        exp += [f"{t('fgm')} / {t('fga')}", f"{100*t('fgm')/t('fga'):.1f}%" if t('fga') else 'N/A', f"{t('tpm')} / {t('tpa')}", str(t('pts'))]
        got = [app, dnp, closed, fg, fgp, tp, pts]
    else:
        got = [app, dnp, closed]
    if got != exp: problems.append(('headline', head, got, exp))
    # located attempts by zone
    zc = Counter(); zm = Counter()
    for g in ap:
        for s in g['result'].get('shots') or []:
            if s.get('player_id') == 'Dwyane Wade':
                zc[s['zone']] += 1; zm[s['zone']] += s['made']
    ztab = [l for l in rows if l.startswith('| Paint') or l.startswith('| Outside') or l.startswith('| 18 ft') or l.startswith('| Three')]
    shown = {}
    for l in ztab:
        c = [x.strip() for x in l.strip().strip('|').split('|')]
        shown[c[0]] = c
    tot_loc = sum(int(c[-1]) for c in shown.values()) if shown and all(c[-1].isdigit() for c in shown.values()) else None
    if tot_loc is not None and tot_loc != sum(zc.values()):
        problems.append(('located', head, tot_loc, sum(zc.values())))
    if shown and 'Three-point range' in shown and shown['Three-point range'][-1].isdigit():
        three = sum(1 for g in ap for s in (g['result'].get('shots') or []) if s.get('player_id') == 'Dwyane Wade' and s['value'] == 3)
        if int(shown['Three-point range'][-1]) != three: problems.append(('3pt-loc', head, shown['Three-point range'][-1], three))
print('sections', n, 'problems', len(problems))
for p in problems[:30]: print(p)
