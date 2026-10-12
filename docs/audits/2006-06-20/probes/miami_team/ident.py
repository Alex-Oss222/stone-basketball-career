import sys; sys.path.insert(0,'/home/user/stone-basketball-career')
from pathlib import Path
from runtime.free_agency_2004 import identity
root=Path('/home/user/stone-basketball-career')
ids=identity(root, 2005)
for b in ('telfase01','smithjo02','gilled01','wilksmi01','carroma01','johnsan02','stevede01','jonesju01','slokaur01'):
    print(b, ids.get(b))
