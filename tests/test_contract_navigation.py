"""Contract navigation covers every tracked identity without changing evidence."""
import json
from pathlib import Path
import re
import tempfile
import unittest

from runtime.contract_navigation import (build_contract_navigation, contract_page, league_player_links,
                                         navigation_block, plain_player_name)
from scripts.format_league_reports import format_page, read_tables

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "career/Dwyane_Wade"


class ContractNavigationTests(unittest.TestCase):
    def test_every_registered_player_is_linked_from_every_league_period(self):
        registry = json.loads((PLAYER / "Stats_and_Awards/League/player_registry.json").read_text())
        expected = {entry["name"]: entry["registry_id"] for entry in registry["players"]}
        outputs = build_contract_navigation(ROOT, PLAYER)
        pages = list((PLAYER / "Stats_and_Awards/League").rglob("League_Stats.md"))
        self.assertEqual(len(expected), registry["player_count"])
        self.assertGreaterEqual(len(expected), 407)
        self.assertGreater(len(pages), 1)
        for page in pages:
            before = [row for _, rows in read_tables(page.read_text()) for row in rows]
            after = [row for _, rows in read_tables(outputs[page]) for row in rows]
            self.assertEqual({plain_player_name(row["Player"]) for row in after}, set(expected))
            for original, linked in zip(before, after):
                name = plain_player_name(linked["Player"])
                self.assertTrue(f"Players/{expected[name]}.md" in linked["Player"]        # the league card (hub)
                                or f"Contracts/players/{expected[name]}.html#contract" in linked["Player"], linked["Player"])
                self.assertEqual({k: v for k, v in original.items() if k != "Player"},
                                 {k: v for k, v in linked.items() if k != "Player"})
            self.assertEqual(outputs[page], league_player_links(outputs[page], page, PLAYER, registry))

    def test_personnel_links_leave_assessment_and_final_sections_unchanged(self):
        outputs = build_contract_navigation(ROOT, PLAYER)
        cards = [page for page in outputs if page.parent.name == "Player_Cards" and page.name != "README.md" and "2003-04" in page.parts]
        register = json.loads((PLAYER / "2003-04/00_Team/Team/Roster/roster.json").read_text(encoding="utf-8"))["players"]
        self.assertEqual(len(cards), len(register))          # one personnel card per register entry on the live date
        for page in cards:
            before, after = page.read_text(), outputs[page]
            self.assertIn("[Current contract]", after)
            self.assertIn("[Contract history]", after)
            self.assertEqual(before.split("## Scouting report", 1)[1], after.split("## Scouting report", 1)[1])
            self.assertEqual(re.findall(r"^\*\*Contract/control:.*$", before, re.M),
                             re.findall(r"^\*\*Contract/control:.*$", after, re.M))

    def test_formatter_preserves_linked_names_and_remains_idempotent(self):
        page = PLAYER / "Stats_and_Awards/League/2003-04/League_Stats.md"
        registry = json.loads((PLAYER / "Stats_and_Awards/League/player_registry.json").read_text())
        asset = page.parents[1] / "assets/per_game.svg"
        first = format_page(page.read_text(), page, registry, "2003-06-26", asset)
        self.assertIn("[Dwyane Wade]", first)
        self.assertEqual(first, format_page(first, page, registry, "2003-06-26", asset))

    def test_navigation_replacement_is_idempotent_and_rejects_broken_marker(self):
        text = "# Example\n\n**Contract/control:** Unsigned.\n\n## Scouting report\nUnassessed.\n"
        first = navigation_block(text, "Current · History", after=r"^\*\*Contract/control:\*\*[^\n]*$")
        self.assertEqual(first, navigation_block(first, "Current · History", after=r"unused"))
        with self.assertRaisesRegex(ValueError, "Malformed"):
            navigation_block(first.replace("<!-- contract-navigation:end -->", ""), "x", after=r"unused")

    def test_unavailable_contract_terms_do_not_prevent_identity_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            player = root / "career/Example"
            league = player / "Stats_and_Awards/League"
            league.mkdir(parents=True)
            registry = {"players": [{"name": "Unknown Terms", "registry_id": "unknown01"}]}
            (league / "player_registry.json").write_text(json.dumps(registry))
            page = league / "League_Stats.md"
            page.write_text("| Player | PTS |\n| --- | --- |\n| Unknown Terms | N/A |\n")
            result = build_contract_navigation(root, player)[page]
            self.assertIn("unknown01.html#contract", result)
            self.assertIn("| N/A |", result)

    def test_navigation_identity_cannot_escape_contract_directory(self):
        with self.assertRaises(ValueError):
            contract_page(PLAYER, "../other-player")


if __name__ == "__main__":
    unittest.main()
