"""Run the generator's compute_totals (read-only) for each season; compare to stored file and to names in results."""
import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime.season_evidence import compute_totals
ROOT = '/home/user/stone-basketball-career/career/Dwyane_Wade/Stats_and_Awards/League'
for s in ('2003-04', '2004-05', '2005-06'):
    gen = compute_totals(s)
    try:
        st = {r['bbr_id']: r for r in json.load(open(f'{ROOT}/{s}/season_totals.json'))['records']}
        same = all(st.get(b, {}).get('totals') == r['totals'] for b, r in gen.items()) and set(st) == set(gen)
    except FileNotFoundError:
        st, same = None, 'no stored file'
    print(s, 'generator records', len(gen), 'stored equal to generator:', same)
    names = {r['player_name'] for r in gen.values()}
    for n in ('simiewa01', 'walshma01', 'allenma01', 'Randy Holcomb'):
        print('   ', n, 'present' if n in names else 'absent')
