"""No code past the first season builds the 2003 market directly (its cap, pool and standings are 2003's): every
caller asks `season_market.for_date`, which returns the 2003 market only in 2003-04."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"runtime/season_market.py", "runtime/market.py",
           "scripts/correct_camp_signings.py", "scripts/correct_minimum_salaries.py"}   # 2003 one-off repairs
PATTERN = re.compile(r"from (?:runtime|\.)\.?market import Market\b|from \.market import Market\b|from runtime\.market import Market\b")


class SeasonMarketGuard(unittest.TestCase):
    def test_no_direct_2003_market(self):
        offenders = []
        for path in sorted(list((ROOT / "runtime").glob("*.py")) + list((ROOT / "scripts").glob("*.py"))):
            rel = path.relative_to(ROOT).as_posix()
            if rel in ALLOWED:
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if PATTERN.search(line) and "for_date" not in line:
                    offenders.append(f"{rel}: {line.strip()}")
        self.assertEqual(offenders, [], "use runtime.season_market.for_date for a dated market")


if __name__ == "__main__":
    unittest.main()
