import re, calendar
from indep import LEAGUE
def scope(page, season):
    parts = page.relative_to(LEAGUE / season).parts
    y0 = int(season[:4])
    start, end = f"{y0}-06-01", f"{y0+1}-06-30"
    if len(parts) >= 2 and re.fullmatch(r"\d{2}_\w+", parts[0]):
        num = int(parts[0][:2]); year = y0 + (num < 7); last = calendar.monthrange(year, num)[1]
        start, end = f"{year}-{num:02d}-01", f"{year}-{num:02d}-{last:02d}"
        if parts[1].startswith('Week_'):
            w = int(parts[1][5:])
            start = f"{year}-{num:02d}-{1+(w-1)*7:02d}"; end = f"{year}-{num:02d}-{(w*7 if w < 4 else last):02d}"
    return start, end

