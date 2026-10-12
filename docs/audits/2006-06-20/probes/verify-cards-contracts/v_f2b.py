exec(open('v_f2_period_team.py').read().split("mismatch = Counter()")[0])
wrong=Counter(); multi=Counter(); wc=set(); mc=set(); ex=[]
for p in reg:
    pid = p['registry_id']
    text = (CARDS/f'{pid}.md').read_text()
    recs = [r for r in lines.get(pid, []) if r.get('line') and r['line'].get('appeared')]
    for line in text.splitlines():
        m = rowre.match(line)
        if not m: continue
        label, folder, age, team = m.groups(); team=team.strip()
        MONS={'November':11,'December':12,'January':1,'February':2,'March':3,'April':4}
        if 'week' in label:
            mm = re.match(r'(\w+) (\d{4}) week \d+ \((\d+) to (\d+)\)', label); mon=MONS[mm.group(1)]; y=int(mm.group(2))
            sc=(f'{y}-{mon:02d}-{int(mm.group(3)):02d}', f'{y}-{mon:02d}-{int(mm.group(4)):02d}'); kind='week'
        elif label.startswith('2005-06'):
            sc=('2005-10-01','2006-04-30'); kind='season'
        else:
            mm=re.match(r'(\w+) (\d{4})',label); mon=MONS[mm.group(1)]; y=int(mm.group(2))
            sc=('2005-10-01' if mon==11 else f'{y}-{mon:02d}-01', f'{y}-{mon:02d}-{calendar.monthrange(y,mon)[1]:02d}'); kind='month'
        clubs = sorted({r['team'] for r in recs if sc[0] <= r['date'] <= sc[1]})
        if not clubs: continue
        codes = {code_of.get(c, c) for c in clubs} | set(clubs)
        if team not in codes:
            wrong[kind]+=1; wc.add(pid)
            if pid in ('jonesju01',) or len(ex)<6: ex.append((pid,label,team,clubs))
        elif len(clubs)>1:
            multi[kind]+=1; mc.add(pid)
print('wrong club', wrong, sum(wrong.values()), len(wc))
print('multi club with card club among them', multi, sum(multi.values()), len(mc))
for e in ex: print(e)
