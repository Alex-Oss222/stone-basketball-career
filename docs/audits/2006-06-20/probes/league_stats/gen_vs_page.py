"""Regenerate a past season's league pages in memory with the generator (write_back.statistics_pages, no writes) and diff."""
import sys; sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
from runtime import write_back as wb
season = sys.argv[1]
root = Path('/home/user/stone-basketball-career')
out = wb.statistics_pages(root, season)
import difflib
n = 0
for page, text in out.items():
    old = page.read_text()
    if old != text:
        n += 1
        d = [l for l in difflib.unified_diff(old.splitlines(), text.splitlines(), lineterm='', n=0) if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))]
        print(page.relative_to(root), len(d))
        for l in d[:6]: print('   ', l[:300])
print('changed', n, 'of', len(out))
