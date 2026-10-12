import sys; sys.path.insert(0,'/home/user/stone-basketball-career')
from pathlib import Path
from runtime import jerseys
root=Path('/home/user/stone-basketball-career')
print('GONE', jerseys.GONE)
print('register', jerseys.register_path(root))
n=jerseys.miami_numbers(root)
for k,v in n.items(): print(k, v)
print('wade', jerseys.wade_number(root))
