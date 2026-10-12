import json, glob, os, collections, unicodedata, re
R='/home/user/stone-basketball-career'
def norm(s): return re.sub(r'[^a-z ]','',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()).strip()
recs=[]
def walk(x, f):
    if isinstance(x,dict):
        b=None
        for k in ('birth_date','date_of_birth','born','dob'):
            v=x.get(k)
            if isinstance(v,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',v): b=v
        if b:
            nm=x.get('name') or x.get('player') or x.get('player_id') or x.get('full_name')
            recs.append(dict(file=f, bbr=x.get('bbr_id') or x.get('nba_id'), name=nm if isinstance(nm,str) else None, birth=b, note={k:v for k,v in x.items() if 'birth' in k and k not in('birth_date',)}))
        for v in x.values(): walk(v,f)
    elif isinstance(x,list):
        for v in x: walk(v,f)
files=glob.glob(R+'/library/**/*.json', recursive=True)+[R+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json']
for f in files:
    if os.path.getsize(f)>60e6: continue
    try: walk(json.load(open(f)), f.replace(R+'/',''))
    except Exception as e: pass
print('records', len(recs))
targets={'Roko Ukic':None,'Ibrahim Kutluay':'kutluib01',"Boniface Ndong":'ndongbo01','Dalibor Bagaric':'bagarda01','Francisco Garcia':'garcifr01','Peter John Ramos':'ramospe01'}
reg={p['registry_id']:p for p in json.load(open(R+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
for nm,b in targets.items():
    rn=reg.get(b,{}).get('name') if b else None
    keys={norm(nm)} | ({norm(rn)} if rn else set())
    hits=[r for r in recs if (b and r['bbr']==b) or (r['name'] and norm(r['name']) in keys) or (r['name'] and norm(nm).split()[-1] in norm(r['name']) and norm(nm).split()[0][:4] in norm(r['name']))]
    c=collections.defaultdict(list)
    for h in hits: c[h['birth']].append(h['file'].split('/')[-1])
    print(nm, b, 'registry:', reg.get(b,{}).get('birth_date') if b else None)
    for k,v in c.items(): print('   ', k, sorted(set(v))[:8])
