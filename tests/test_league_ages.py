"""League statistics pages show each player's age on the page's cutoff (the period's end, or the career date while it runs)
from his registry birth date (runtime/write_back.league_page), not the age recorded when his row was first added."""
import json
import re
import unittest
from pathlib import Path

from runtime.league_cards import age_on
from runtime.stat_layout import scope_for
from runtime.write_back import clock

ROOT = Path(__file__).resolve().parents[1]
LEAGUE = ROOT / "career/Dwyane_Wade/Stats_and_Awards/League"


def cutoff(page):
    """The page's cutoff, as league_page reads it: the period's end, or the career date while it runs."""
    now = clock(ROOT)
    return min(scope_for(page, [], now)["end"], now)


def ages(page):
    text = page.read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in re.finditer(r"^\| \[([^\]]+)\]\([^)]*\) \| (\S+) \|", text, re.M)}


class LeagueAgeTests(unittest.TestCase):
    def test_closed_season_pages_use_the_season_end(self):
        births = {p["name"]: p.get("birth_date") for p in json.loads((LEAGUE / "player_registry.json").read_text())["players"]}
        page = LEAGUE / "2004-05/League_Stats.md"
        shown, day = ages(page), cutoff(page)
        for name in ("LeBron James", "Dwight Howard", "Kevin Garnett", "Dwyane Wade"):
            self.assertEqual(shown[name], str(age_on(births[name], day)), name)

    def test_every_league_page_age_is_at_its_cutoff(self):
        births = {p["name"]: p.get("birth_date") for p in json.loads((LEAGUE / "player_registry.json").read_text())["players"]}
        for page in sorted(LEAGUE.rglob("League_Stats.md")):
            shown, day = ages(page), cutoff(page)
            for name, age in shown.items():
                if births.get(name) and age.isdigit():
                    self.assertEqual(age, str(age_on(births[name], day)), f"{page}: {name}")


if __name__ == "__main__":
    unittest.main()
