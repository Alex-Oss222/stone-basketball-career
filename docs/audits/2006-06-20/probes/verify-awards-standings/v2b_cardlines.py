import sys, json, pickle
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
R = Path('/home/user/stone-basketball-career')
from runtime import league_cards
lab = pickle.load(open('lab.pkl','rb'))
tx = json.loads((R/league_cards.TRANSACTIONS).read_text())
clubs = sorted({c for _, _, cnt in lab for c in cnt})
code = {c: league_cards._code(c, tx, {}) for c in clubs}
print(code)
never, minority = [], []
for name, lbl, cnt in lab:
    played_codes = {code[c]: n for c, n in cnt.items()}
    tot = sum(cnt.values())
    if lbl not in played_codes:
        never.append((name, lbl, dict(cnt)))
    elif len(cnt) > 1 and played_codes[lbl] < tot / 2:
        minority.append((name, lbl, dict(cnt)))
print('label never played for:', len(never))
for x in never: print('  ', x)
print('label is a minority stint:', len(minority))
for x in minority: print('  ', x)
