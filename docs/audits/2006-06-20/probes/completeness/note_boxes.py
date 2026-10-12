"""Every played Miami note's box-score text block against its declared result file: every player line of both
clubs (MIN, PTS, FG, 3P, FT, OR, DR, AST, STL, BLK, TO, PF), team lines, period scores and header score."""
import glob, json, re, os
W = '/home/user/stone-basketball-career/career/Dwyane_Wade'
bad, n_notes, n_rows = [], 0, 0
for note in sorted(glob.glob(W + '/20*/0[5-9]_*/**/Game_*.md', recursive=True) + glob.glob(W + '/20*/11_All_Star/**/Game_*.md', recursive=True)):
    text = open(note, encoding='utf-8').read()
    m = re.search(r'^result_file: (\S+)', text, re.M)
    if not m or 'status: played' not in text:
        continue
    res = json.load(open(os.path.join(os.path.dirname(note), m.group(1))))
    box = re.search(r'### Box score\n\n```text\n(.*?)```', text, re.S)
    if not box:
        bad.append((note, 'no box')); continue
    n_notes += 1
    lines = box.group(1).splitlines()
    rows = {}
    current = None
    for ln in lines:
        if ln.strip() in (res['home'], res['away']):
            current = 'home' if ln.strip() == res['home'] else 'away'
            continue
        mm = re.match(r'^(.+?)\s{2,}(\d+\.\d)\s+(\d+)\s+(\d+)-(\d+)\s+(\d+)-(\d+)\s+(\d+)-(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$', ln)
        if mm and current:
            rows[(current, re.sub(r' \((DQ|ej\.?|EJ)\)$', '', mm.group(1).strip()))] = [float(mm.group(2))] + [int(x) for x in mm.groups()[2:]]
    for side in ('home', 'away'):
        for p in res['player_stats'][side]:
            key = (side, p['player_id'])
            exp = [round(p['seconds'] / 60, 1), p['pts'], p['fgm'], p['fga'], p['tpm'], p['tpa'], p['ftm'], p['fta'], p['orb'], p['drb'], p['ast'], p['stl'], p['blk'], p['tov'], p['pf']]
            got = rows.get(key)
            if got is None:
                # name may be truncated in the text block
                cand = [k for k in rows if k[0] == side and p['player_id'].startswith(k[1][:20])]
                got = rows.get(cand[0]) if cand else None
            n_rows += 1
            if got is None and not (p.get('seconds') or 0) > 0:
                continue
            if got is None:
                bad.append((note.split('Dwyane_Wade/')[1], 'missing row', p['player_id']))
            elif abs(got[0] - exp[0]) > 0.11 or got[1:] != exp[1:]:
                bad.append((note.split('Dwyane_Wade/')[1], side, p['player_id'], got, exp))
        t = rows.get((side, 'TEAM'))
        if t and t[1] != res['final_score'][side]:
            bad.append((note, 'team pts', side, t[1], res['final_score'][side]))
print('notes', n_notes, 'player rows', n_rows, 'issues', len(bad))
for b in bad[:25]:
    print(b)
