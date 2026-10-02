"""Evidence gates and market/legal separation using synthetic player scenarios."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from runtime.player_market_profile import (
    ROOT, build_profile, demo_profiles, estimate_market, load_2003_comparables,
    salary_bounds, select_status,
)

ON = "2003-07-16"
CAP = {"as_of": "2003-07-15", "source_ref": "test:published-cap",
       "amount": 43840000, "season": "2003-04", "basis": "published"}
CONTROL = {"as_of": "2003-07-01", "source_ref": "test:expired-contract",
           "state": "expired", "effective_on": "2003-07-01", "rfa_eligible": True}
QO = {"as_of": "2003-06-30", "source_ref": "test:valid-qualifying-offer",
      "status": "active", "timely": True, "valid": True, "rights_preserved": True}


def control(**changes):
    return dict(deepcopy(CONTROL), **changes)


def bounds(**changes):
    args = dict(on=ON, season="2003-04", years_of_service=4, prior_salary=2500000, cap=CAP)
    args.update(changes)
    return salary_bounds(**args)


class StatusTests(unittest.TestCase):
    def test_selectable_scenario_preserves_live_draft_rights(self):
        live = {"as_of": "2003-06-26", "source_ref": "test:draft", "state": "draft_rights"}
        original = deepcopy(live)
        result = select_status(on="2003-06-26", mode="scenario", selected_status="UFA", control=live)
        self.assertEqual(result["effective_status"], "UFA")
        self.assertEqual(result["live_status"], "draft_rights")
        self.assertTrue(result["is_hypothetical"])
        self.assertEqual(live, original)
        with self.assertRaises(ValueError):
            select_status(on=ON, selected_status="UFA", control=live)

    def test_missing_and_future_control_remain_unknown(self):
        for evidence in (None, {}, control(as_of="2003-07-17")):
            result = select_status(on=ON, control=evidence)
            self.assertEqual(result["live_status"], "unknown")
            self.assertFalse(result["evidence_refs"])

    def test_rfa_eligibility_does_not_establish_rfa(self):
        for qo in (None, dict(QO, timely=False), dict(QO, valid=False),
                   dict(QO, rights_preserved=False), dict(QO, as_of="2003-07-17")):
            result = select_status(on=ON, control=control(qualifying_offer=qo))
            self.assertEqual(result["live_status"], "unknown")
        self.assertEqual(select_status(on=ON, control=control(qualifying_offer=QO))["live_status"], "RFA")

    def test_no_tender_is_not_final_before_deadline(self):
        qo = {"as_of": "2003-06-26", "source_ref": "test:qo-outcome",
              "status": "not_tendered", "deadline": "2003-06-30", "final": True}
        initial = control(as_of="2003-06-26", effective_on="2003-06-26", qualifying_offer=qo)
        self.assertEqual(select_status(on="2003-06-26", control=initial)["live_status"], "unknown")
        self.assertEqual(select_status(on=ON, control=initial)["live_status"], "UFA")

    def test_only_valid_withdrawal_becomes_unrestricted(self):
        qo = dict(QO, status="withdrawn")
        self.assertEqual(select_status(on=ON, control=control(qualifying_offer=qo))["live_status"], "unknown")
        qo["valid_withdrawal"] = True
        self.assertEqual(select_status(on=ON, control=control(qualifying_offer=qo))["live_status"], "UFA")

    def test_contract_option_waiver_and_expiry_gates(self):
        for state in ("under_contract", "option_pending", "draft_rights"):
            self.assertEqual(select_status(on=ON, control=control(state=state))["live_status"], state)
        released = control(state="released", rfa_eligible=False)
        self.assertEqual(select_status(on=ON, control=released)["live_status"], "waivers_pending")
        released["waivers_cleared"] = True
        self.assertEqual(select_status(on=ON, control=released)["live_status"], "UFA")
        self.assertEqual(select_status(on=ON, control=control(effective_on="2003-07-17"))["live_status"], "unknown")


class ValuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo = demo_profiles()
        cls.production = cls.demo["roles"][1]["production"]
        cls.comps = load_2003_comparables(on=ON)

    def estimate(self, **changes):
        args = dict(on=ON, production=self.production, comparables=self.comps, cap=CAP)
        args.update(changes)
        return estimate_market(**args)

    def test_unknown_or_zero_games_is_not_a_minimum_contract(self):
        invalid = deepcopy(self.production)
        invalid["totals"]["games"] = 0
        for production in (None, {}, invalid, dict(self.production, as_of="2004-04-14")):
            value = self.estimate(production=production)
            self.assertEqual(value["status"], "unavailable")
            self.assertIsNone(value["target"])

    def test_future_player_results_and_cap_cannot_change_estimate(self):
        value = self.estimate(cap=dict(CAP, as_of="2003-07-17"))
        self.assertIsNone(value["target"])
        base = self.estimate()
        future = deepcopy(self.comps[0])
        future.update(id="future-star", salary=100000000, as_of="2003-07-17")
        variant = self.estimate(comparables=self.comps + [future])
        self.assertEqual(base["target"], variant["target"])
        self.assertEqual(base["comparable_count"], variant["comparable_count"])
        self.assertNotIn("future-star", [c["id"] for c in variant["comparables"]])

    def test_comparable_cap_has_its_own_knowledge_gate(self):
        comps = deepcopy(self.comps)
        for row in comps:
            row["cap_known_on"] = "2003-07-17"
        self.assertIsNone(self.estimate(comparables=comps)["target"])

    def test_rookie_unverified_duplicate_and_low_sample_comps_excluded(self):
        baseline = self.estimate()
        extras = []
        for i, kind in enumerate(("rookie_scale", "unverified")):
            row = deepcopy(self.comps[0])
            row.update(id=f"bad-{i}", salary_kind=kind, salary=500000000)
            extras.append(row)
        extras.append(deepcopy(self.comps[0]))
        low = deepcopy(self.comps[0])
        low["id"] = "low-sample"
        low["totals"]["minutes"] = 10
        extras.append(low)
        result = self.estimate(comparables=self.comps + extras)
        self.assertEqual(result["target"], baseline["target"])
        self.assertEqual(result["excluded_count"], baseline["excluded_count"] + 4)

    def test_salary_scales_with_cap_but_cap_share_is_stable(self):
        base = self.estimate()
        result = self.estimate(cap=dict(CAP, amount=CAP["amount"] * 2, basis="scenario"))
        self.assertEqual(base["cap_share_target"], result["cap_share_target"])
        self.assertAlmostEqual(base["target"] * 2, result["target"], delta=1)
        self.assertLess(base["low"], base["target"])
        self.assertLess(base["target"], base["high"])

    def test_market_value_is_not_clipped_to_maximum(self):
        star = self.demo["roles"][2]["market_value"]
        self.assertGreater(star["target"], bounds()["maximum"])
        self.assertIsNone(bounds()["offer_ceiling"])

    def test_low_sample_and_unknown_age_reduce_confidence(self):
        p = deepcopy(self.production)
        p["totals"]["minutes"] = 200
        self.assertEqual(self.estimate(production=p)["confidence"], "low")
        p = dict(self.production, age=None)
        self.assertEqual(self.estimate(production=p)["confidence"], "low")

    def test_no_fit_from_missing_or_degenerate_comparables(self):
        self.assertIsNone(self.estimate(comparables=self.comps[:4])["target"])
        rows = [dict(deepcopy(self.comps[0]), id=f"same-{i}") for i in range(5)]
        self.assertIsNone(self.estimate(comparables=rows)["target"])

    def test_repeatable_json_fixture_and_inputs_unchanged(self):
        original = deepcopy((self.production, self.comps, CAP))
        self.estimate()
        self.assertEqual((self.production, self.comps, CAP), original)
        json.dumps(self.demo, allow_nan=False)
        self.assertEqual(self.demo, demo_profiles())
        fixture = json.loads((ROOT / "docs/examples/player_milestones/player_market_profile.example.json").read_text())
        self.assertEqual(fixture, self.demo)

    def test_inventory_metadata_and_contract_dates_are_gated(self):
        from runtime.player_market_profile import BASELINE, CONTRACTS, STATS
        data = {str(ROOT / p): json.loads((ROOT / p).read_text()) for p in (BASELINE, CONTRACTS, STATS)}
        def fake_read(path, *args, **kwargs):
            return json.dumps(data[str(path)])
        data[str(ROOT / CONTRACTS)]["as_of"] = "2003-07-17"
        with patch.object(Path, "read_text", fake_read):
            self.assertEqual(load_2003_comparables(on=ON), [])
        data[str(ROOT / CONTRACTS)]["as_of"] = "2003-06-26"
        player = next(p for c in data[str(ROOT / CONTRACTS)]["clubs"].values()
                      for p in c["players"] if p.get("bbr_id") == self.comps[0]["id"])
        player["signed_date"] = "2003-07-01"
        with patch.object(Path, "read_text", fake_read):
            ids = {p["id"] for p in load_2003_comparables(on=ON)}
            self.assertNotIn(player["bbr_id"], ids)
        player.pop("signed_date")
        player["amount_kind"]["2003-04"] = "player_option"
        with patch.object(Path, "read_text", fake_read):
            ids = {p["id"] for p in load_2003_comparables(on=ON)}
            self.assertNotIn(player["bbr_id"], ids)

    def test_proxy_has_low_predictive_confidence_and_explicit_basis(self):
        value = self.estimate()
        self.assertEqual(value["confidence"], "low")
        self.assertEqual(value["model"]["comparable_basis"], "scheduled_salary_proxy")
        for comparable in value["comparables"]:
            self.assertEqual(comparable["salary_season"], "2003-04")
            self.assertEqual(comparable["normalization_cap"], 43840000)
            self.assertEqual(comparable["cap_known_on"], "2003-07-15")


class SalaryBoundsTests(unittest.TestCase):
    def test_exact_service_minimum_does_not_use_two_year_fallback(self):
        self.assertEqual(bounds(years_of_service=4)["minimum"], 688679)
        self.assertEqual(bounds(years_of_service=9)["minimum"], 1000000)
        self.assertEqual(bounds(years_of_service=12)["minimum"], 1070000)
        self.assertIsNone(bounds(years_of_service=None)["minimum"])

    def test_prepublication_cap_cannot_be_used_as_legal_maximum(self):
        early = bounds(on="2003-06-26", cap=CAP)
        self.assertIsNone(early["maximum"])
        self.assertIsNone(early["service_tier_maximum"])
        planning = dict(CAP, as_of="2002-07-16", amount=40271000, basis="prior_season_planning")
        self.assertIsNone(bounds(cap=planning)["maximum"])

    def test_prior_salary_unknown_is_distinct_from_known_zero(self):
        self.assertEqual(bounds(prior_salary=0)["maximum"], 10960000)
        unknown = bounds(prior_salary=None)
        self.assertEqual(unknown["service_tier_maximum"], 10960000)
        self.assertIsNone(unknown["maximum"])
        self.assertEqual(bounds(prior_salary=14000000)["maximum"], 14700000)

    def test_team_capacity_is_separate_from_player_max_and_market_worth(self):
        route = {"as_of": ON, "source_ref": "test:cap-room", "name": "room",
                 "verified": True, "capacity": 5000000}
        result = bounds(route=route)
        self.assertEqual(result["maximum"], 10960000)
        self.assertEqual(result["offer_ceiling"], 5000000)
        self.assertEqual(result["contract_legality"], "not_evaluated")
        self.assertIsNone(bounds(route=dict(route, verified=False))["offer_ceiling"])
        self.assertIsNone(bounds(route=dict(route, as_of="2003-07-17"))["offer_ceiling"])
        self.assertEqual(bounds(route=dict(route, capacity=100000))["status"], "no_first_year_capacity")
        self.assertEqual(bounds(route=dict(route, capacity=0))["route_ceiling"], 0)
        self.assertEqual(bounds(route=dict(route, capacity=0))["status"], "no_first_year_capacity")

    def test_unknown_era_table_fails_closed(self):
        result = bounds(season="2026-27")
        self.assertIsNone(result["minimum"])
        self.assertIsNone(result["maximum"])

    def test_current_checkpoint_has_no_fabricated_free_agency_or_value(self):
        result = demo_profiles()["current_checkpoint"]
        self.assertEqual(result["eligibility"]["live_status"], "draft_rights")
        self.assertIsNone(result["market_value"]["target"])
        self.assertIsNone(result["legal_bounds"]["minimum"])
        self.assertIsNone(result["legal_bounds"]["maximum"])
        self.assertEqual(result["actions"], ["review_rookie_scale"])
        self.assertFalse(result["execution_enabled"])

    def test_live_profile_rejects_scenario_cap(self):
        with self.assertRaises(ValueError):
            build_profile(on=ON, cap=dict(CAP, basis="scenario"))

    def test_profile_rejects_later_agreement(self):
        with self.assertRaises(ValueError):
            build_profile(on="2026-07-16")


if __name__ == "__main__":
    unittest.main()
