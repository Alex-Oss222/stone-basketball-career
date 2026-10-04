"""Exercise the real card JavaScript against closed-game cohort aggregates.

The small DOM adapter runs renderers and their event handlers; browser layout
and keyboard navigation remain covered by the interactive review.
"""
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

from tests.test_live_player_cards import LiveCardFixtures, box


TEMPLATE = Path(__file__).resolve().parents[1] / "runtime/assets/player_cards.html"
NODE = shutil.which("node")
RUN_CARD = r"""
const fs = require('fs'), vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
class Element {
  constructor() { this.dataset = {}; this.style = {}; this.listeners = {};
    this.innerHTML = ''; this.textContent = ''; this.hidden = false;
    this.classList = {toggle() {}}; }
  addEventListener(event, handler) { this.listeners[event] = handler; }
  setAttribute() {} toggleAttribute() {} focus() {} append() {} remove() {}
  querySelector(selector) {
    if (selector === 'img') return null;
    return this.child || (this.child = new Element());
  }
}
const elements = new Map();
const get = id => {
  if (!elements.has(id)) elements.set(id, new Element());
  return elements.get(id);
};
get('player-card-data').textContent = JSON.stringify(input.data);
const location = {};
const locate = href => {
  const url = new URL(href, 'https://example.test');
  Object.assign(location, {pathname:url.pathname, search:url.search, hash:url.hash});
};
locate(input.url || '/player_cards.html#shooting');
const context = vm.createContext({URLSearchParams, location,
  history: {replaceState: (_state, _title, href) => locate(href)},
  document: {getElementById: get, querySelector: get, querySelectorAll: () => [],
    createElement: () => new Element()},
  window: {addEventListener() {}}, Image: Element,
});
vm.runInContext(input.script, context);
vm.runInContext(input.actions || '', context);
const result = vm.runInContext(`({
  scope:cohortScope(), gp:appearances(period()), box:period().box,
  detail:detailSelection(), coverage:tracking(), cohort:cohortSummary(),
  view:$('player-view').innerHTML, inspector:$('spot-detail').innerHTML,
  source:sourceNote(), sources:sourceGames(), court:courtSVG(),
  trackedDisabled:$('cohort-select').querySelector('option[value="tracked"]').disabled,
  contractLink:{hidden:$('footer-contract-link').hidden, href:$('footer-contract-link').href},
  identityCutoff:$('identity-cutoff').textContent, identityStatus:$('identity-status').textContent,
  url:location.pathname+location.search+location.hash,
})`, context);
process.stdout.write(JSON.stringify(result));
"""


def card_view(data, actions="", url=None):
    script = re.search(r"<script>\s*([\s\S]*?)</script>", TEMPLATE.read_text()).group(1)
    completed = subprocess.run(
        [NODE, "-e", RUN_CARD], text=True, capture_output=True, check=False,
        input=json.dumps(dict(data=data, script=script, actions=actions, url=url)))
    if completed.returncode:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout)


@unittest.skipUnless(NODE, "Node is required to execute the card renderer")
class TrackedShotViewTests(LiveCardFixtures):
    def mixed_period(self):
        self.game("Game_1", "2003-11-01", line=box(fgm=14, fga=28, tpm=0, tpa=0, pts=30))
        note, _, raw = self.game("Game_2", "2003-11-02")
        self.feed(note, raw)
        note, _, raw = self.game("Game_3", "2003-11-03", line=box(fgm=0, fga=0, tpm=0, tpa=0, pts=2))
        self.feed(note, raw, shots=[])
        data = self.data()
        data["default_period"] = self.season(data)["id"]
        return data

    def test_partial_period_defaults_to_complete_cohort_and_its_denominators(self):
        data = self.mixed_period()
        result = card_view(data)
        self.assertEqual((result["scope"], result["gp"], result["box"]["pts"]), ("tracked", 2, 6))
        self.assertEqual(result["coverage"]["status"], "complete")
        self.assertEqual(result["detail"]["fg_ppg"], 1)
        self.assertEqual(result["detail"]["fga_per_game"], 1)
        self.assertRegex(result["view"], r'Total points / game</div><div class="metric-value">3\.0<')
        self.assertIn("Tracked games only · 2 GP", result["cohort"])
        self.assertIn("2003-11-02 to 2003-11-03", result["cohort"])
        self.assertIn("2 of 3 appearances fully tracked", result["cohort"])
        self.assertNotIn("2003-11-01", result["sources"])
        self.assertIn("2003-11-03", result["sources"])
        zone = card_view(data, "selectZone('paint');")
        self.assertEqual((zone["detail"]["fg_ppg"], zone["detail"]["fga_per_game"]), (1, .5))
        cluster = card_view(data, "selectBin(period().shooting.bins[0].id);")
        self.assertEqual(cluster["detail"]["area_weight"], .5)
        self.assertIn("2 appearances", cluster["inspector"])

    def test_all_games_selection_restores_full_box_totals_and_withholds_partial_chart(self):
        result = card_view(self.mixed_period(), "$('cohort-select').listeners.change({target:{value:'all'}});")
        self.assertEqual((result["scope"], result["gp"], result["box"]["pts"]), ("all", 3, 36))
        self.assertRegex(result["view"], r'Total points / game</div><div class="metric-value">12\.0<')
        self.assertEqual(result["coverage"]["status"], "partial")
        self.assertIsNone(result["detail"]["fg_ppg"])
        self.assertNotIn('class="shot-bin', result["court"])
        self.assertIn("Choose Tracked games only", result["view"])
        self.assertIn("2003-11-01", result["sources"])
        self.assertIn("cohort=all", result["url"])

    def test_tracked_dates_do_not_backdate_the_period_identity(self):
        data = self.mixed_period()
        self.season(data)["identity"]["status"] = "Role recorded on November 30"
        result = card_view(data)
        self.assertEqual(result["identityCutoff"], "Through 2003-11-30")
        self.assertEqual(result["identityStatus"], "Role recorded on November 30")
        self.assertIn("2003-11-02 to 2003-11-03", result["cohort"])
        all_games = card_view(data, "changeCohort('all');")
        self.assertEqual(all_games["identityCutoff"], result["identityCutoff"])

    def test_explicit_cohort_survives_period_tab_and_shared_url(self):
        data = self.mixed_period()
        month = next(p for p in data["periods"] if p["kind"] == "month")
        actions = "changeCohort('all');changePeriod(%s);changeTab('contract');changeTab('shooting');" % json.dumps(month["id"])
        changed = card_view(data, actions)
        reopened = card_view(data, url=changed["url"])
        self.assertIn("cohort=all", changed["url"])
        self.assertIn("period=" + month["id"], changed["url"])
        self.assertEqual((reopened["scope"], reopened["box"]), ("all", changed["box"]))
        selected = card_view(data, "changeCohort('tracked');")
        self.assertEqual(card_view(data, url=selected["url"])["scope"], "tracked")

    def test_historical_only_period_explains_future_tracking_without_demo_dots(self):
        self.game()
        data = self.data()
        data["default_period"] = self.season(data)["id"]
        result = card_view(data, url="/player_cards.html?cohort=tracked#shooting")
        self.assertEqual((result["scope"], result["gp"]), ("all", 1))
        self.assertTrue(result["trackedDisabled"])
        self.assertIn("No fully tracked games", result["cohort"])
        self.assertIn("Future tracked engine games will populate this chart", result["view"])
        self.assertNotIn('class="shot-bin', result["court"])
        self.assertIsNone(result["detail"]["fga_per_game"])

    def test_manual_and_engine_provenance_stay_distinct(self):
        data = self.mixed_period()
        manual = card_view(data)
        self.assertIn("RECORDED LOCATION DATA", manual["source"])
        self.assertNotIn("SIMULATED ENGINE", manual["source"])
        for period in data["periods"]:
            if period.get("tracked"):
                period["tracked"]["shot_source_type"] = "engine_generated"
                period["tracked"]["source_note"] = "Simulated engine locations."
                for game in period["tracked"]["source_games"]:
                    game["shot_source_type"] = "engine_generated"
                    game["shot_source_label"] = "Simulated engine shot locations"
        engine = card_view(data)
        self.assertIn("SIMULATED ENGINE LOCATIONS", engine["source"])
        self.assertIn("Simulated engine shot locations", engine["sources"])
        for period in data["periods"]:
            if period.get("tracked"):
                period["tracked"]["shot_source_type"] = "mixed"
        self.assertIn("SIMULATED ENGINE LOCATIONS AND RECORDED TRACKING", card_view(data)["source"])

    def test_complete_period_defaults_to_all_and_legacy_payload_remains_supported(self):
        note, _, raw = self.game()
        self.feed(note, raw)
        data = self.data()
        data["default_period"] = self.season(data)["id"]
        self.assertEqual(card_view(data)["scope"], "all")
        legacy = deepcopy(data)
        for period in legacy["periods"]:
            period.pop("tracked", None)
            period.pop("tracking_cohort", None)
        result = card_view(legacy)
        self.assertEqual(result["scope"], "all")
        self.assertEqual(result["coverage"]["status"], "complete")
        self.assertEqual(result["cohort"], "")

    def test_league_tabs_keep_external_contract_navigation(self):
        data = self.mixed_period()
        data["enabled_tabs"] = ["shooting", "awards"]
        data["links"]["contract"] = "../Contracts/player.html#contract"
        result = card_view(data)
        self.assertEqual(result["contractLink"], dict(hidden=False, href=data["links"]["contract"]))
        self.assertEqual(result["scope"], "tracked")


if __name__ == "__main__":
    unittest.main()
