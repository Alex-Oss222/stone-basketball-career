# Player market profile baseline

The milestone screens can now use a deterministic, read-only baseline in [`runtime/player_market_profile.py`](../runtime/player_market_profile.py). It supports a selectable UFA/RFA **scenario**, an independently derived live control status, an explainable estimate of first-year salary, and separate salary/route bounds. It does not create club offers, record player consent, sign a contract, advance time, or write career state.

The June 26, 2003 Wade checkpoint remains unsigned Miami draft rights. No NBA production, free-agent status, qualifying offer, 2003-04 published cap, or new contract is invented for him. His draft-rights profile points to the rookie workflow and leaves veteran salary bounds empty.

## What the player sees

| Display | Meaning | What it does not establish |
| --- | --- | --- |
| Live status | State derived from supplied dated contract/control facts | A selectable new career status |
| Scenario selector: UFA / RFA | Preview a possible future negotiation situation | Expiry, waiver clearance, a QO, or a rights change |
| Theoretical worth: low / target / high | Heuristic first-year salary estimate from dated production and existing veteran salaries | A firm bid, guaranteed total, or legal signing range |
| Cap share | Dollar estimate divided by the stated cap denominator | An automatically legal maximum salary |
| Player minimum / maximum | Service-specific limits, when evidence supports them | A particular team's ability to pay |
| Team route ceiling | Externally verified remaining capacity under the named route | Verification of term, raises, bonuses, options, timing or all contract law |
| Preparation actions | Relevant next items to inspect or discuss | Executable accept, sign, match, trade or commit actions |

A change from UFA to RFA changes the assumed decision process, including an outside offer sheet. It does not apply an arbitrary RFA salary discount. Actual buyer demand, a valid QO alternative and willingness to risk matching belong in the agent dossier and independently issued team proposals.

## Run it

From the repository root:

```bash
python -m runtime.player_market_profile
python -m unittest tests.test_player_market_profile
```

The module prints JSON only. It does not save anything. The checked-in [`player_market_profile.example.json`](examples/player_milestones/player_market_profile.example.json) is generated from `demo_profiles()` and explicitly marked `example_only`. It contains three synthetic guard-production presets, both selectable market scenarios, and the separate June 26 draft checkpoint. Its league comparison evidence is real dated inventory; its player production and scenario rights are illustrative, never Wade's simulated results.

Regenerate the example when changing this model:

```bash
python -m runtime.player_market_profile > docs/examples/player_milestones/player_market_profile.example.json
```

## Callable interface

```python
from runtime.player_market_profile import build_profile, demo_profiles

example = demo_profiles()
restricted_scenario = example["profiles"]["RFA"]
band = restricted_scenario["market_value"]
assert restricted_scenario["execution_enabled"] is False

profile = build_profile(
    on="2003-07-16",
    mode="scenario",
    selected_status="UFA",
    control={
        "as_of": "2003-06-26",
        "source_ref": "example:unsigned-draft-rights",
        "state": "draft_rights",
    },
    # Supply dated NBA production, comparables and a cap to calculate worth.
    # Missing evidence returns unavailable, never an invented minimum deal.
)
assert profile["eligibility"]["live_status"] == "draft_rights"
assert profile["eligibility"]["effective_status"] == "UFA"
assert profile["market_value"]["target"] is None
```

`build_profile` accepts `on`, `mode`, `selected_status`, `control`, `production`, `comparables`, `cap`, `season`, `years_of_service`, `prior_salary`, `route`, and an optional repository `root`. Dates use `YYYY-MM-DD`. `on` is the supplied view date, not a command to change the career clock. A live adapter must obtain that date from authoritative state. The profile rejects dates outside the 1999-agreement era; its published-maximum implementation supports 2003-04 only. A later season needs a separately researched adapter.

Its component functions are `select_status`, `estimate_market`, `salary_bounds`, and `load_2003_comparables`. Each returns ordinary JSON-safe structures, and none mutates its inputs.

## Status input and missing information

Every accepted evidence object needs a nonempty `source_ref` and an `as_of` no later than the view date. These fields are adapter assertions. The module checks their shape and timing but cannot authenticate issuers, open source references, discover newer contrary events, or prove their contents. A client must not be allowed to self-certify live rights.

`control` contains:

| Field | Values / responsibility |
| --- | --- |
| `state` | `draft_rights`, `under_contract`, `option_pending`, `expired`, or `released` |
| `effective_on` | Required for expiry/release; must have arrived |
| `waivers_cleared` | Must be `true` after release; otherwise `waivers_pending` |
| `rfa_eligible` | Verified `true` or `false`; omitted/null is unknown |
| `qualifying_offer` | Separate dated, sourced decision object for an eligible player |

Contract state takes precedence over a free-agency assertion. `draft_rights`, an existing contract, or an unresolved option stays visible. Eligibility alone does not make a player restricted. A fourth-year first-round player and a qualifying younger veteran reach that status through the applicable 1999 eligibility rule **and** a timely valid qualifying offer. A declined fourth-year option has different consequences and must be classified correctly by the upstream rights adapter.

For an active QO, use `status: "active"`, `timely: true`, `valid: true`, and `rights_preserved: true`. For a final missed tender, use `status: "not_tendered"`, `final: true`, and the actual `deadline`; that date must have passed. For a withdrawal, use `status: "withdrawn"` and `valid_withdrawal: true` only after verifying that withdrawal was permissible and effective. Merely observing no QO on June 26 does not prove no tender by June 30. An unverified or future-dated QO leaves live status unknown.

`mode: "live"` rejects a `selected_status`. `mode: "scenario"` requires `UFA` or `RFA`, preserves `live_status` beside the chosen `effective_status`, and labels the necessary hypothetical expiry/clearance/rights assumptions. No return value constitutes the external eligibility attestation required by [`contract_negotiation.py`](contract_negotiation_engine.md).

## Production and comparable evidence

`production` has `as_of`, `source_ref`, optional `age`, and `totals`. Required totals are games, minutes, points, offensive and defensive rebounds, assists, steals, blocks, field-goal attempts and makes, free-throw attempts and makes, and turnovers. Games and minutes must be positive; all values must be finite and nonnegative; makes cannot exceed attempts. Unknown production and zero games yield `unavailable`, not a zero-value or minimum-salary player.

For Wade, the caller must supply only closed simulated NBA results through the career date, preserving links to those results. Do not substitute real Wade NBA history, college totals, anticipated next-season totals, engine talent trajectories or scouting grades. Other established NBA players may use the dated historical baseline. The generic API does not itself authenticate or aggregate games.

Each comparable has `id`, optional `label`, `as_of`, `source_ref`, `salary_kind: "veteran_contract"`, positive `salary`, positive normalization `cap`, `cap_known_on`, `totals`, optional `age`, `salary_season`, `signed_date`, and `basis`. Duplicate IDs, rookie-scale/unverified contracts, future evidence/caps, fewer than 500 minutes, missing production and malformed rows are excluded. At least five eligible, nonidentical production observations and a positive price relationship are required. The result reports the eligible and excluded counts.

The repository loader uses the June 26, 2003 contract inventory and prior-season statistics. It validates their metadata dates and refuses newer replacement datasets. It admits only `under_contract` rows whose 2003-04 `amount_kind` is `contract_salary`, excludes supplied signing dates after the inventory cutoff, and excludes rookie scale, unresolved continuity, pending options and prospective free-agent deals. A missing signing date remains explicitly unknown; some inventory obligations are reconstructed from a salary pattern, as documented in the source. It reads neither offseason exits nor real-career trajectories. It is a fixed 2003 adapter, not an automatically rolling market feed.

The loader returns **2003-04 scheduled salaries on existing deals**, including later years of older contracts. Those are not new-deal first-year signing comparables. Each visible nearest comparison includes its salary season, signing date when known, age, denominator cap and cap knowledge date. The output names this fallback `scheduled_salary_proxy`.

## Explainable price model

The production transform reuses `runtime.valuation.production_value`, including its existing named judgment constants:

1. Compute box-score efficiency per game: points + rebounds + assists + steals + blocks, less missed field goals, missed free throws and turnovers.
2. Shrink toward efficiency 5 with weight `minutes / (minutes + 500)` and apply the existing age factor. Missing age uses a neutral factor and reduces evidence coverage.
3. Fit `log(scheduled_salary / normalization_cap) = intercept + slope * production_value` across all admitted veteran contracts.
4. Apply the fitted relationship to the supplied player's production, then multiply the predicted cap share by the supplied cap to express a first-year-dollar estimate.
5. Set the log-band width to the greater of `log(1.25)` and `1.4826 * median absolute deviation` of fit residuals. Add `0.20 * 500 / (player_minutes + 500)` for a small player sample. Add `0.25` if production falls outside the comparable range. Low/high are `exp(predicted_log_share +/- width)` times the cap.

The five displayed nearest players explain local context; they are not the only records fitted. The returned model exposes its intercept, slope, band width and extrapolation flag. Its range is a judgment range, not a confidence interval, percentile interval or offer probability. `confidence` remains `low` because this scheduled-salary proxy has not been validated against held-out new contracts. `evidence_coverage` can be moderate when production and sample coverage are sufficient; that label does not raise predictive confidence.

Existing salaries reflect earlier negotiation, age at signing, bargaining rules, guarantees and possible overpayment. The estimate omits direct health assessment, defense beyond box-score events, playoff scouting, fit, cap competition and private team bids. It must not be described as a calibrated fair-value model. Signed-date-normalized comparable deals and held-out validation are an improvement path, not implemented functionality.

There is no separate automatic PPG, assists, age, award or potential premium on top of the same evidence. Contract comparisons should discuss independently supported health, role and market facts visibly rather than hiding unsupported adjustments inside a dollar score. A player can be worth more than the legal maximum in this heuristic, or less than the minimum; that is why the unclipped estimate and salary rules remain separate.

## Cap evidence, legal limits and club capacity

`cap` contains `as_of`, `source_ref`, `amount`, `season`, and `basis`: `published`, `prior_season_planning`, or `scenario`. The model can size planning dollars with a prior cap, visibly labeled. A live profile rejects a scenario cap. The 2003 loader uses $40,271,000 before July 15 and $43,840,000 afterward. Reading a later source to reconstruct an existing salary does not authorize importing a later cap, signing or option result.

`salary_bounds` uses the full service-specific 1999 minimum table. It does not fall back from, for example, a four-year veteran to the two-year minimum. `years_of_service` unknown leaves limits unresolved. That count must be legally verified, not blindly equated to seasons with an appearance.

For 2003-04, the published service-tier maximum becomes available on July 15 with the matching sourced season cap. The player's actual maximum is the greater of that tier and 105% of verified prior salary. `prior_salary: 0` is a known zero; `None` means the alternative is unresolved, so `maximum` remains null while `service_tier_maximum` can still display the published tier. Before publication, a planning cap never turns into a confirmed maximum. Fixed minimum-scale figures agreed under the CBA are separate from the subsequently published cap.

A `route` contains `as_of`, `source_ref`, `name`, `verified: true`, and integer-dollar `capacity`. Names are `room`, `bird`, `early_bird`, `non_bird`, `mid_level`, `million`, or `minimum`. Capacity is the **already independently checked remaining amount**, after relevant holds, other commitments and route restrictions. The module does not calculate it. Zero is a known zero and produces `no_first_year_capacity`; missing evidence is incomplete. Unknown names fail closed.

When both player maximum and route capacity are known, `offer_floor` is the applicable minimum and `offer_ceiling` is the lesser of maximum and capacity. This is only a first-year screen. It does not approve term, raises, incentives, guarantees, partial-season treatment, QO acceptance, offer-sheet content or timing. `contract_legality` always remains `not_evaluated`, and `execution_enabled` is always false. A draft-rights profile does not present these veteran bounds as a rookie-scale signing range.

## Integration and verification

Feed the view from authenticated career/rights/production/cap adapters. Keep draft scenario inputs outside career records. Source changes must regenerate the view; a previously valid snapshot is not proof that no later event occurred. Do not map a displayed target salary directly into a club-issued offer. Clubs decide what to offer, and the user decides only the player's legitimate response.

The existing repository already has the Miami front-office market, GM, negotiation and signing modules. This baseline does not replace them or certify every check they perform. The remaining work is an authenticated player-dashboard adapter that consumes this profile, supplies complete source-backed legality and timing checks, records the player's actual decision, and hands off to the applicable execution workflow. The isolated contract workflow and its adapter boundary are described in [`contract_negotiation_engine.md`](contract_negotiation_engine.md).

Tests cover live/scenario separation, draft rights, unresolved options, expiry, waivers, RFA eligibility versus QO evidence, missed/withdrawn tenders, future evidence exclusion, exact service minima, unknown prior salary, published-cap gating, unknown versus zero route capacity, uncapped market worth, deterministic fixtures and input immutability.

Historical rule references: 1999 CBA Article XI Sections 4-6 for fourth-year options and restricted status, Article II Section 7 for maximum salary, and the service minimum table recorded in `nba_1999_cba_minimum_salary_scale.json`. See the source audit in [the contract research guide](templates/player_milestones/contract_negotiation_research.md) and [the milestone research guide](templates/player_milestones/player_experience_research.md) for primary-text links and the separate 2003 calendar override. The code is intentionally narrower than a comprehensive legal engine.
