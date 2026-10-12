"""Run the Team page generator read-only for every season and diff against disk (ignoring the As-of date line)."""
import sys, re, difflib
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime import write_back
root = Path('/home/user/stone-basketball-career')
for s in ('2003-04', '2004-05', '2005-06'):
    out = write_back.statistics_pages(root, s)
    diffs = 0
    for page, text in out.items():
        if 'Stats_and_Awards/Team' not in str(page):
            continue
        old = page.read_text()
        norm = lambda t: re.sub(r'^As of [^:]*:', 'As of X:', t, flags=re.M)
        if norm(old) != norm(text):
            diffs += 1
            if diffs <= 3:
                d = list(difflib.unified_diff(norm(old).splitlines(), norm(text).splitlines(), lineterm='', n=0))
                print(page.relative_to(root), '\n'.join(d[:20]))
    print(s, 'team pages differing beyond the As-of date:', diffs)
