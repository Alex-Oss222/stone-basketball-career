"""Independent recomputation of Chris Bosh's followed-player pages from closed results."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/completeness')
from results_lib import *
from datetime import date

NAME = 'Chris Bosh'
CLUB = 'Toronto Raptors'
BIRTH = date(1984, 3, 24)

def lines(season, kind):
    out = []
    for p, d, req in results(season, kind):
        for side in ('home', 'away'):
            for row in d['player_stats'].get(side, []):
                if row['player_id'] == NAME:
                    m = bbr_map(req, side)
                    if m and m.get(NAME) not in (None, 'boshch01'):
                        print('BBR MISMATCH', p, m.get(NAME))
                    team = d[side]
                    opp = d['away' if side == 'home' else 'home']
                    out.append(dict(row, date=d['game_date'], team=team, opp=opp, venue=side, event=d['event_id'], season=season, kind=kind))
    return sorted(out, key=lambda r: (r['date'], r['event']))

def agg(rows):
    rows = [r for r in rows if (r.get('seconds') or 0) > 0 or r.get('appeared')]
    g = len(rows)
    if not g:
        return None
    t = lambda k: sum(r.get(k) or 0 for r in rows)
    fga, fgm, tpa, tpm, fta, ftm, pts = t('fga'), t('fgm'), t('tpa'), t('tpm'), t('fta'), t('ftm'), t('pts')
    return dict(gp=g, gs=sum(1 for r in rows if r.get('started')), mpg=t('seconds') / 60 / g, ppg=pts / g,
                rpg=(t('orb') + t('drb')) / g, apg=t('ast') / g, spg=t('stl') / g, bpg=t('blk') / g,
                fg=100 * fgm / fga if fga else None, tp=100 * tpm / tpa if tpa else None, ft=100 * ftm / fta if fta else None,
                ts=100 * pts / (2 * (fga + 0.44 * fta)) if fga or fta else None, pts=pts)

def fmt(a):
    f = lambda x: 'N/A' if x is None else f'{x:.1f}'
    return f"{a['gp']}/{a['gs']} | {f(a['mpg'])} | {f(a['ppg'])} | {f(a['rpg'])} | {f(a['apg'])} | {f(a['spg'])} | {f(a['bpg'])} | {f(a['fg'])} | {f(a['tp'])} | {f(a['ft'])} | {f(a['ts'])}"

def record(season):
    w = l = 0
    for p, d, req in results(season, 'regular'):
        if CLUB in (d['home'], d['away']):
            side = 'home' if d['home'] == CLUB else 'away'
            other = 'away' if side == 'home' else 'home'
            if d['final_score'][side] > d['final_score'][other]:
                w += 1
            else:
                l += 1
    return w, l

def playoff_exit(season):
    series = {}
    for p, d, req in results(season, 'playoff'):
        if CLUB in (d['home'], d['away']):
            opp = d['away'] if d['home'] == CLUB else d['home']
            side = 'home' if d['home'] == CLUB else 'away'
            other = 'away' if side == 'home' else 'home'
            s = series.setdefault(opp, [0, 0, d['game_date']])
            s[0 if d['final_score'][side] > d['final_score'][other] else 1] += 1
            s[2] = max(s[2], d['game_date'])
    return sorted(series.items(), key=lambda kv: kv[1][2])

if __name__ == '__main__':
    allg = []
    for s in ('2003-04', '2004-05', '2005-06'):
        reg, po = lines(s, 'regular'), lines(s, 'playoff')
        allg += reg + po
        print(s, 'regular', fmt(agg(reg)), 'record', record(s))
        print(s, 'playoff', fmt(agg(po)) if agg(po) else None, 'series', playoff_exit(s))
        teams = {r['team'] for r in reg + po}
        print('  teams', teams, 'zero-second rows', sum(1 for r in reg + po if not (r.get('seconds') or 0) > 0))
        app = [r for r in reg if (r.get('seconds') or 0) > 0]
        for key, lab in (('pts', 'Points'), ('reb', 'Rebounds'), ('ast', 'Assists'), ('stl', 'Steals'), ('blk', 'Blocks'), ('tpm', 'Threes'), ('ftm', 'FT')):
            val = (lambda r: r['orb'] + r['drb']) if key == 'reb' else (lambda r, k=key: r.get(k) or 0)
            top = max(val(r) for r in app)
            hits = [r for r in app if val(r) == top]
            print(f"   high {lab}: {top} {hits[0]['date']} {'vs' if hits[0]['venue']=='home' else 'at'} {hits[0]['opp']} (+{len(hits)-1})")
    # career totals
    reg_all = [r for r in allg if r['kind'] == 'regular' and (r.get('seconds') or 0) > 0]
    po_all = [r for r in allg if r['kind'] == 'playoff' and (r.get('seconds') or 0) > 0]
    tot = lambda rows, k: sum((r['orb'] + r['drb']) if k == 'reb' else (r.get(k) or 0) for r in rows)
    print('career regular', {k: tot(reg_all, k) for k in ('pts', 'reb', 'ast', 'stl', 'blk', 'tpm', 'ftm')}, 'gp', len(reg_all))
    print('career playoff', {k: tot(po_all, k) for k in ('pts', 'reb', 'ast')}, 'gp', len(po_all))
    # milestones
    def cross(rows, key, thr):
        c = 0
        for i, r in enumerate(rows, 1):
            c += 1 if key == 'gp' else ((r['orb'] + r['drb']) if key == 'reb' else (r.get(key) or 0))
            if c >= thr:
                d = date.fromisoformat(r['date'])
                return r['date'], i, r['opp'], (d - BIRTH).days
        return None
    for key, thrs in (('pts', [1000, 2000, 3000, 4000]), ('reb', [250, 500, 1000, 1500, 2000]), ('blk', [100, 250]), ('stl', [100]),
                      ('ast', [250, 500]), ('ftm', [500]), ('gp', [100, 200])):
        for t in thrs:
            print('  reg', key, t, cross(reg_all, key, t))
    for key, thrs in (('pts', [100, 250, 500]), ('gp', [10, 25, 50]), ('reb', [100, 250, 500]), ('ast', [100])):
        for t in thrs:
            print('  po', key, t, cross(po_all, key, t))
    # firsts
    def first(cond):
        for r in reg_all:
            if cond(r):
                return r['date'], r['opp'], r['pts'], r['orb'] + r['drb'], r['ast']
    print('debut', first(lambda r: True))
    print('20pt', first(lambda r: r['pts'] >= 20)); print('30pt', first(lambda r: r['pts'] >= 30)); print('40pt', first(lambda r: r['pts'] >= 40))
    dd = lambda r: sum(1 for v in (r['pts'], r['orb'] + r['drb'], r['ast'], r['stl'], r['blk']) if v >= 10) >= 2
    print('dd', first(dd)); print('5blk', first(lambda r: r['blk'] >= 5)); print('15reb', first(lambda r: r['orb'] + r['drb'] >= 15))
    print('10ast', first(lambda r: r['ast'] >= 10)); print('20reb', first(lambda r: r['orb'] + r['drb'] >= 20))
    print('td', first(lambda r: sum(1 for v in (r['pts'], r['orb'] + r['drb'], r['ast'], r['stl'], r['blk']) if v >= 10) >= 3))
