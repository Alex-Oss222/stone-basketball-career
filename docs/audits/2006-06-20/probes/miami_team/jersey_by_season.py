"""Miami numbers the jersey rule gives when each season is the live one (runtime/jerseys.py, read-only)."""
import sys; sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime import jerseys
root = Path('/home/user/stone-basketball-career')
for s in ('2003-04', '2004-05', '2005-06'):
    jerseys._season = lambda root=None, s=s: s
    try:
        n = jerseys.miami_numbers(root)
    except Exception as e:
        print(s, 'error', e); continue
    print(s, {k: v for k, v in n.items() if k in ('Caron Butler', 'Dwyane Wade', 'Eddie Jones', 'Mike James', 'Brian Grant')}, 'wade_number', jerseys.wade_number(root))
