"""Every game log lists exactly the games its period owns; every closed game is on one week page."""
import re
from pathlib import Path
from compare import games, scope_from_path, CAREER, LINK
from collections import Counter

def game_log_links(page):
    text = page.read_text()
    if '### Game log' not in text: return None
    sec = text.split('### Game log', 1)[1]
    out = []
    for line in sec.splitlines()[1:]:
        if line.startswith('###'): break
        if line.startswith('| [') :
            m = re.match(r'\| \[([^\]]+)\]\(([^)]+)\) \| ([^|]*) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|', line)
            out.append(((page.parent / m.group(2)).resolve(), m.group(1), m.group(3).strip(), m.group(4).strip(), m.group(5).strip(), m.group(6).strip()))
    return out

problems = []; checked = 0
week_cover = Counter()
for page in sorted(CAREER.rglob('*.md')):
    rel = page.relative_to(CAREER)
    if 'League' in rel.parts or 'Team' in rel.parts[:2]: continue
    logs = game_log_links(page)
    if logs is None: continue
    sc = scope_from_path(page) if not (page.name.startswith('Game_')) else None
    if page.name.startswith('Game_'):
        continue
    if sc is None:
        continue
    checked += 1
    exp = {g['path'] for g in sc['games']}
    got = [l[0] for l in logs]
    if len(got) != len(set(got)): problems.append(('dup', str(rel)))
    if set(got) != exp: problems.append(('set', str(rel), [str(p) for p in exp - set(got)], [str(p) for p in set(got) - exp]))
    # check each log row's opponent/venue/result/participation vs note meta
    for path, label, opp, ven, res, part in logs:
        g = next(g for g in games if g['path'] == path)
        m = g['meta']
        if label != m['date'] or opp != m['opponent'] or ven != m['venue'] or res != m['result']:
            problems.append(('row', str(rel), label, opp, ven, res, m['date'], m['opponent'], m['venue'], m['result']))
        expected_part = {'played': 'Played', 'dnp': 'DNP', 'missing': 'Unknown'}[g['cov']]
        if not part.startswith(expected_part):
            problems.append(('participation', str(rel), label, part, g['cov']))
    if rel.parts[0] == 'Stats_and_Awards' and 'Week_' in str(rel) and page.name == 'README.md':
        for p in got: week_cover[p] += 1
reg = [g for g in games if g['comp'] == 'regular' and g['status'] == 'played']
missing = [g['note'] for g in reg if week_cover[g['path']] != 1]
print('checked pages', checked, 'problems', len(problems)); [print(p) for p in problems[:30]]
print('regular games', len(reg), 'not on exactly one Stats week page', missing[:10])
