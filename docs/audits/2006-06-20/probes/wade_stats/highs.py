from compare import games
for s in ('2003-04', '2004-05', '2005-06'):
    sel = sorted([g for g in games if g['season'] == s and g['comp'] == 'regular' and g['status'] == 'played' and g['cov'] == 'played'], key=lambda g: g['date'])
    print('==', s)
    for lab, f in (('PTS', lambda r: r['pts']), ('REB', lambda r: r['orb'] + r['drb']), ('AST', lambda r: r['ast']), ('STL', lambda r: r['stl']),
                   ('BLK', lambda r: r['blk']), ('FGM', lambda r: r['fgm']), ('3PM', lambda r: r['tpm']), ('FTM', lambda r: r['ftm']), ('MIN', lambda r: r['seconds'] / 60)):
        hi = max(f(g['row']) for g in sel)
        ties = [(g['date'], g['meta']['venue'], g['meta']['opponent']) for g in sel if f(g['row']) == hi]
        print(lab, round(hi, 2) if lab == 'MIN' else hi, ties[0], '+%d' % (len(ties) - 1) if len(ties) > 1 else '')
    mins = sorted(((g['row']['seconds'] / 60, g['date']) for g in sel), reverse=True)[:3]
    print('top minutes', mins)
