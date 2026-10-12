import json, sys
sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime.league_cards import age_on
R='/home/user/stone-basketball-career'
reg={p['registry_id']:p for p in json.load(open(R+'/career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json'))['players']}
ids=['wrighdo01','thomajo02','evansma01','bakerma01','edwarjo01','robinbe01','drejech01','slokaur01']
births=json.load(open(R+'/library/careers/nba_player_births.json'))
print(type(births), list(births.keys())[:5] if isinstance(births,dict) else births[:1])
bp=births['players']
print(type(bp), (list(bp.items())[:1] if isinstance(bp,dict) else bp[:1]))
def find_all(obj, key):
    out=[]
    def w(x):
        if isinstance(x,dict):
            if any(x.get(k)==key for k in ('bbr_id','registry_id','id','player_id')) or key in x and isinstance(x[key],(dict,str)):
                out.append(x if any(x.get(k)==key for k in ('bbr_id','registry_id','id','player_id')) else {key:x[key]})
            for v in x.values(): w(v)
        elif isinstance(x,list):
            for v in x: w(v)
    w(obj); return out
pe4=json.load(open(R+'/library/2004/league/nba_2004_prospect_evidence.json'))
pe5=json.load(open(R+'/library/2005/league/nba_2005_prospect_evidence.json'))
names={'wrighdo01':'Dorell Wright','thomajo02':'John Thomas','evansma01':'Maurice Evans','bakerma01':'Maurice Baker','edwarjo01':'John Edwards','robinbe01':'Bernard Robinson','drejech01':'Christian Drejer','slokaur01':'Slokar'}
def by_name(obj,name):
    out=[]
    def w(x):
        if isinstance(x,dict):
            if isinstance(x.get('name'),str) and name.split()[-1] in x['name'] and (len(name.split())==1 or name.split()[0][:3] in x['name']):
                out.append({k:v for k,v in x.items() if 'birth' in k or k in('name','bbr_id','age_on_draft_day')})
            for v in x.values(): w(v)
        elif isinstance(x,list):
            for v in x: w(v)
    w(obj); return out
for i in ids:
    r=reg.get(i)
    b=[ (k,v) for k,v in (bp.items() if isinstance(bp,dict) else []) if k==i]
    if not b and isinstance(bp,list): b=[x for x in bp if x.get('bbr_id')==i]
    print(i, 'registry:', r and r.get('birth_date'), '| births:', b, '| pe4:', by_name(pe4,names[i]), '| pe5:', by_name(pe5,names[i]))
for i,d in [('wrighdo01','1985-12-02'),('robinbe01','1980-12-26'),('edwarjo01','1981-07-31'),('bakerma01','1979-07-28'),('evansma01','1978-11-08'),('thomajo02','1975-09-08'),('drejech01','1982-12-08')]:
    print(i, age_on(d,'2004-10-01'))
print('slokar', age_on('1983-05-14','2005-10-01'))
