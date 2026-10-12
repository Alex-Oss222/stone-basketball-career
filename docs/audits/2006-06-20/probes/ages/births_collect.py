import json, sys, glob, collections, unicodedata, re
sys.path.insert(0, '/home/user/stone-basketball-career')
ROOT='/home/user/stone-basketball-career'
FIELDS=('birth_date','date_of_birth','born','birthdate','dob')
def key(n):
    n=unicodedata.normalize('NFKD',n or '').encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z]','',n)
recs=[]
def walk(x,file,path,ctx):
    if isinstance(x,dict):
        b=None
        for f in FIELDS:
            v=x.get(f)
            if isinstance(v,dict): v=v.get('value')
            if isinstance(v,str) and re.match(r'^\d{4}-\d{2}-\d{2}',v):
                b=(f,v[:10])
        if b:
            bb=x.get('bbr_id') or x.get('bbr')
            if isinstance(bb,dict): bb=bb.get('value')
            name=x.get('name') or x.get('player') or x.get('player_id') or x.get('full_name') or ctx.get('key')
            recs.append(dict(file=file,path=path,bbr=bb or (ctx.get('key') if isinstance(ctx.get('key'),str) and re.match(r'^[a-z]{2,7}\d\d$',ctx.get('key') or '') else None),name=name,birth=b[1],field=b[0]))
        for k,v in x.items():
            walk(v,file,path+'/'+str(k),{'key':k})
    elif isinstance(x,list):
        for i,v in enumerate(x): walk(v,file,f'{path}[{i}]',ctx)
files=[f for f in glob.glob(ROOT+'/**/*.json',recursive=True) if '/tests/' not in f and '/Games/' not in f and not f.endswith('.result.json') and not f.endswith('.request.json')]
for f in files:
    try:
        txt=open(f).read()
    except Exception: continue
    if not any(fl in txt for fl in FIELDS): continue
    try: d=json.loads(txt)
    except Exception: continue
    walk(d,f.replace(ROOT+'/',''),'',{})
json.dump(recs,open('/tmp/claude-0/-home-user-stone-basketball-career/11006769-3a09-5e04-99fe-2171d43ad26e/scratchpad/audit/ages/birth_records.json','w'))
print(len(recs))
print(collections.Counter(r['file'] for r in recs).most_common(60))
