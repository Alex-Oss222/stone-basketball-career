import json, glob, re, os
R='/home/user/stone-basketball-career'
def playoff_results(s):
    out={}
    for note in glob.glob(f'{R}/career/Dwyane_Wade/{s}/08_Playoffs/**/*.md', recursive=True):
        t=open(note).read()
        m=re.search(r'^status: (\S+)',t,re.M); rf=re.search(r'^result_file: (\S+)',t,re.M)
        if not m or m.group(1)!='played' or not rf: continue
        d=json.load(open(os.path.join(os.path.dirname(note),rf.group(1))))
        out[d['event_id']]=('miami',d)
    for p in glob.glob(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/Playoffs/Games/*.result.json'):
        d=json.load(open(p))
        if d['event_id'] in out: print('dup',d['event_id'])
        out[d['event_id']]=('league',d)
    return out
for s in ['2003-04','2004-05','2005-06']:
    res=playoff_results(s)
    pj=json.load(open(f'{R}/career/Dwyane_Wade/Stats_and_Awards/League/{s}/playoffs.json'))
    used=set()
    print(s,'playoff results',len(res))
    for se in pj['series']:
        wins={c:0 for c in se['clubs']}
        for g in se['games']:
            r=res.get(g['event_id'])
            if r is None:
                if g.get('result') or g.get('winner'): print(' result missing for',g['event_id'])
                continue
            d=r[1]; used.add(g['event_id'])
            if d.get('game_type')!='playoff': print(' type',d.get('game_type'),g['event_id'])
            if d['home']!=g['home'] or d['away']!=g['away'] or d['game_date']!=g['date']: print(' home/away/date mismatch',g['event_id'])
            w=d['home'] if d['final_score']['home']>d['final_score']['away'] else d['away']
            wins[w]+=1
            exp=f"{d['away']} {d['final_score']['away']}, {d['home']} {d['final_score']['home']}"
            if g.get('result')!=exp or g.get('winner')!=w: print(' game text mismatch',g['event_id'],g.get('result'),exp)
            if max(wins.values())>4: print(' >4 wins', se['id'])
        if wins!=se['wins']: print(' series wins mismatch',se['id'],wins,se['wins'])
        win=[c for c,v in wins.items() if v==4]
        if (win[0] if win else None)!=se['winner']: print(' winner mismatch',se['id'],win,se['winner'])
        # home court by record
    extra=set(res)-used
    if extra: print(' results not in any series',sorted(extra)[:5],len(extra))
    fin=[x for x in pj['series'] if x['round']=='finals']
    print(' finals',fin[0]['clubs'],fin[0]['wins'],'champion',pj['champion'])
