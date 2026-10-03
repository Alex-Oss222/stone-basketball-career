import json
from pathlib import Path
import re
import unittest

from runtime.contract_pages import build_contract_pages, contract_markdown
from runtime.player_cards import build_player_cards
from runtime.player_contracts import build_contract_catalog
from runtime.stat_layout import ReportStyle

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "career/Dwyane_Wade"
CLOCK = "2003-06-26"


class ContractPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = build_contract_catalog(ROOT, PLAYER, CLOCK)
        cls.pages = build_contract_pages(ROOT, PLAYER, CLOCK, catalog=cls.catalog)
        cls.folder = PLAYER / "Contracts"

    def test_every_registry_player_has_an_independent_html_and_full_record(self):
        registry = json.loads((PLAYER / "Stats_and_Awards/League/player_registry.json").read_text())
        catalog_ids = {p["id"] for p in self.catalog["players"]}
        self.assertTrue({p["registry_id"] for p in registry["players"]} <= catalog_ids)
        for player in self.catalog["players"]:
            html = self.pages[self.folder / "players" / f'{player["id"]}.html']
            payload = json.loads(re.search(r'<script id="player-card-data" type="application/json">(.*?)</script>', html, re.S)[1])
            self.assertEqual(payload["identity"]["name"], player["name"])
            self.assertEqual(payload["enabled_tabs"], ["contract"])
            self.assertEqual(payload["contracts"]["as_of"], CLOCK)
            self.assertNotIn("__PLAYER_CARD_DATA__", html)
            self.assertIn('src="../assets/player_cards.js"', html)
            md = self.pages[self.folder / "players" / f'{player["id"]}.md']
            self.assertIn("## Current contract", md)
            self.assertIn("## Contract history", md)

    def test_directory_contains_all_ids_and_independent_history_links(self):
        directory = self.pages[self.folder / "index.html"]
        for player in self.catalog["players"]:
            self.assertIn(f'players/{player["id"]}.html#contract"', directory)
            self.assertIn(f'players/{player["id"]}.html#contract-history"', directory)
        self.assertIn('id="search"', directory)
        self.assertIn('id="team"', directory)
        self.assertIn('aria-live="polite"', directory)

    def test_wade_standalone_uses_alternate_identity_and_no_historical_contract(self):
        html = self.pages[self.folder / "players" / f'{self.catalog["default_player_id"]}.html']
        payload = json.loads(re.search(r'<script id="player-card-data" type="application/json">(.*?)</script>', html, re.S)[1])
        self.assertEqual(payload["identity"]["age"], 19)
        self.assertIsNone(payload["contracts"]["current"])
        self.assertEqual(payload["contracts"]["history"], [])
        self.assertNotIn("2003-08-18", html)
        self.assertNotIn("262159355", html)

    def test_main_cards_and_report_banners_use_the_required_order(self):
        identity = json.loads((PLAYER / "professional_identity.json").read_text())
        cards = build_player_cards(ROOT, PLAYER, identity, [], [], CLOCK, contract_catalog=self.catalog)
        folder = PLAYER / "Stats_and_Awards"
        html = cards[folder / "player_cards.html"]
        self.assertLess(html.index('id="tab-shooting"'), html.index('id="tab-contract"'))
        self.assertLess(html.index('id="tab-contract"'), html.index('id="tab-awards"'))
        data = json.loads(cards[folder / "player_cards_data.json"])
        self.assertEqual(data["contracts"]["player_id"], self.catalog["default_player_id"])
        self.assertIn(folder / "Contract.md", cards)
        style = ReportStyle(identity, [], CLOCK, {}, PLAYER / "assets", PLAYER, cards_root=folder,
                            card_periods=["regular-2003-04"], default_card_period="regular-2003-04", detailed=True)
        nav = style.cards_navigation(folder / "README.md")
        self.assertLess(nav.index("[![Shooting]"), nav.index("[![Contract]"))
        self.assertLess(nav.index("[![Contract]"), nav.index("[![Awards]"))

    def test_full_markdown_preserves_terms_not_just_the_summary(self):
        record = dict(id="fixture", title="Recorded agreement", summary="Signed terms", metrics=[dict(label="Guarantee", value="$0", detail="Explicitly unprotected")],
                      sections=[dict(title="Salary schedule", body="Contract schedule basis", columns=["Season", "Salary"], rows=[["2003-04", "$1,000,000"]]),
                                dict(title="Guarantee conditions", notice="Condition not yet met", items=["Guaranteed after the recorded deadline"])],
                      sources=[dict(label="Executed record", href="signed.json")])
        md = contract_markdown(dict(as_of=CLOCK, current=record, history=[record], sections=[], sources=[]), "Fixture Player", interactive="fixture.html")
        for term in ("$0", "Explicitly unprotected", "2003-04", "$1,000,000", "Condition not yet met", "Guaranteed after the recorded deadline", "[Executed record](signed.json)"):
            self.assertIn(term, md)


if __name__ == "__main__":
    unittest.main()
