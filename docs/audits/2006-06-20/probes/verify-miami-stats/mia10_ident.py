import sys
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
R=Path('/home/user/stone-basketball-career')
from runtime.free_agency_2004 import identity
for y in (2004, 2005):
    try:
        d=identity(R, y)
        print(y, d.get('telfase01'))
    except Exception as e: print(y,'err',e)
