import json, glob, os
R='/home/user/stone-basketball-career/career/Dwyane_Wade'
for s in ('2003-04','2004-05','2005-06'):
    for f in sorted(glob.glob(f'{R}/{s}/00_Team/Team/Depth_Chart/Reviews/*/rotation.json'))+sorted(glob.glob(f'{R}/{s}/00_Team/Team/Depth_Chart/rotation.json')):
        d=json.load(open(f))
        found=None
        def walk(x,path=''):
            global found
            if isinstance(x,dict):
                if any('wade' in str(v).lower() for k,v in x.items() if k in('player','name','player_id','id','bbr_id')):
                    for k in ('minutes','planned_minutes','mpg','target_minutes'):
                        if k in x: found=(path,k,x[k]); return
                for k,v in x.items(): walk(v,path+'/'+k)
            elif isinstance(x,list):
                for i,v in enumerate(x): walk(v,path+f'[{i}]')
        walk(d)
        print(f.split('Dwyane_Wade/')[1], found)
