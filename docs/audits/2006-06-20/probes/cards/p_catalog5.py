import sys, json, pickle, collections
sys.path.insert(0, '/home/user/stone-basketball-career')
c = pickle.load(open('catalog_full.pkl','rb'))
truth = pickle.load(open('truth.pkl','rb'))
def season_add(s, n):
    y = int(s[:4]) + n
    return f"{y}-{str(y+1)[-2:]}"
known = []
for p in c['players']:
    cur = p.get('current')
    if not cur: continue
    term = cur.get('original_term_seasons'); start = cur.get('start_season'); end = cur.get('end_season')
    if not end and term and start:
        end = season_add(start, term - 1)
    if end and end < '2005-06':
        known.append((p['id'], p['name'], p['team'], cur['id'], cur['status'], cur.get('team'), start, term, end, cur['full_original_schedule'], (truth.get(p['id']) or (None,''))[0]))
print(len(known))
for k in known: print(k)
