"""Broken relative links on Miami Team pages and Miami personnel cards."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from collect import *
pages = list((CAREER / 'Stats_and_Awards/Team').rglob('*.md'))
for s in SEASONS:
    pages += list((CAREER / s / '00_Team').rglob('*.md'))
broken = {}
for p in pages:
    for m in re.finditer(r'\]\(([^)#\s]+)(?:#[^)]*)?\)', p.read_text()):
        t = m.group(1)
        if t.startswith('http'):
            continue
        if not (p.parent / t).exists():
            broken.setdefault(t, []).append(str(p.relative_to(CAREER)))
for t, ps in broken.items():
    print(t, len(ps), ps[:3])
print('pages', len(pages), 'broken targets', len(broken))
