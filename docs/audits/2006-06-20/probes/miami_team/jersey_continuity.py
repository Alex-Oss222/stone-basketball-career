"""Numbers per live season for every player on Miami's register in two consecutive seasons."""
import sys; sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime import jerseys
root = Path('/home/user/stone-basketball-career')
maps = {}
for s in ('2003-04', '2004-05', '2005-06'):
    jerseys._season = lambda root=None, s=s: s
    maps[s] = jerseys.miami_numbers(root)
names = set().union(*[set(m) for m in maps.values()])
for n in sorted(names):
    seq = [maps[s].get(n, '-') for s in maps]
    present = [x for x in seq if x != '-']
    if len(present) > 1 and len(set(present)) > 1:
        print(n, dict(zip(maps, seq)))
