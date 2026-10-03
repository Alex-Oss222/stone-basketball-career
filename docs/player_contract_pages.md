# Player contract pages

The **Contract** tab sits between **Shooting** and **Awards**. It answers three questions: what agreement or control record exists now, what each recorded season means financially, and which dated events produced the current position. It uses the same player identity and career cutoff as the other cards.

The tab is a detailed record, not a negotiation simulator. Reading it does not create an offer, accept terms, execute a contract, exercise an option, trade a player, or advance the career date. Player responses remain in the established dated workflow. Club-owned decisions remain with the front office.

## Reference and source boundary

Research reviewed October 3, 2026. The supplied [SalarySwish Dwyane Wade page](https://www.salaryswish.com/players/dwyane-wade) is a presentation reference. Its useful structure is a contract summary followed by separate agreements, season-level financial rows, signing provenance, option decisions and transaction notes. It distinguishes salary, cap charges, protection and incentives. We adopt that information hierarchy, not its wording, historical figures, current status, biography or contractual outcomes.

Historical Wade's contract history is not this branch's history. The current branch opens on June 26, 2003 with Miami holding an unsigned first-round pick's rights. A recorded draft hold or scale reference is not a signed agreement. Other tracked players retain their own source-backed records and coverage limitations; missing terms are not completed with historical Wade data or later real-world transactions.

| Source | Era and use | Implementation boundary |
| --- | --- | --- |
| [SalarySwish supplied player page](https://www.salaryswish.com/players/dwyane-wade) | Retrieved October 3, 2026; contract-page layout reference | No page figures or historical player outcomes become career canon |
| [1999 NBA–NBPA CBA, original text hosted by UNH Law](https://ipmall.law.unh.edu/sites/default/files/hosted_resources/SportsEntLaw_Institute/1999NBA_NBPA_CBA.pdf) | Governing historical agreement for the initial 2003 career; check applicable amendments | Article II §§3–4 separates negotiated compensation protection; Article VIII §1 covers rookie terms; Article XI covers options and free agency; Exhibit A §10 addresses assignment |
| [NBA CBA 101, November 2024](https://cms.nba.com/wp-content/uploads/sites/4/2024/11/2024-25-CBA-101.pdf) | Primary modern terminology reference, especially §§II.G, II.I–K | Supports separate presentation of salary, incentives, options, trades and cap accounting; modern limits, exceptions and dates are not 2003 rules |
| [NBPA CBA page](https://nbpa.com/cba) | Primary agreement portal, retrieved October 3, 2026 | The agreement governs employment rights and obligations; a website's convenient labels do not establish a player's legal rights |

The 1999 rookie framework provides three seasons plus a fourth-year team option. Its minimum protection for lack of skill and non-insured injury or illness is 80% **of scale**, not automatically the whole negotiated salary at a higher scale percentage. A missing guarantee record therefore remains unknown. An ordinary trade assigns the existing contract; it does not create another signed agreement. These distinctions come from Article VIII §1 and Exhibit A §10, respectively. This screen does not determine transaction legality from those summaries.

## Financial fields must retain their meaning

The following are the display contract: a calculation may only appear when its stated inputs are known. Unknown, zero, conditional and not applicable are different states.

| Display concept | Meaning | Required handling |
| --- | --- | --- |
| Original signed face value | The full recorded salary schedule of one executed agreement, with option or conditional years identified | Do not infer from a truncated remaining schedule; state whether conditional years are included |
| Recorded schedule total | Sum of the salary amounts actually present in the current record | Identify partial coverage; do not label it the original contract value |
| Guaranteed compensation | Recorded protection, with any conditions, scope and effective dates | Do not substitute salary, cap commitment, roster membership or a default percentage |
| Base salary | Contractual annual salary where the source identifies it as such | Retain the source's precision and any proration basis |
| Cap charge | Amount counted in a team's cap record for a particular season | Keep separate from cash; do not assume it always equals base salary |
| Draft or free-agent hold | Accounting amount attached to unsigned rights or a free agent | Never count as a signed contract, salary earned or guaranteed money |
| Average annual value | A stated full-agreement total divided by the corresponding number of seasons | Withhold if either full value or original term is incomplete; label any option-inclusive denominator |
| Cap percentage | A season's recorded cap charge divided by that same season's published salary cap | Enforce the cap's publication gate; an unpublished denominator is unavailable |
| Likely and unlikely incentives | Separately recorded conditional compensation and classification | Unknown does not mean zero; classification does not prove the bonus was earned |
| Paid or earned compensation | Observed payment or accrual evidence, including relevant adjustments | A salary schedule alone cannot establish cash received or lifetime earnings |
| Dead money or buyout amount | A dated obligation or cap consequence after a termination event | Retain the original agreement and separate adjustment; do not create a second signing |

Totals must not silently mix those categories. An unknown component makes a claimed complete total unavailable. A known subtotal may still be useful if labeled with its coverage. Display rounding must not change the underlying recorded dollar amounts.

No tax, escrow, agent-fee, fine, withholding or net-pay estimate follows merely from contract salary. Those require their own evidence and supported accounting. The absence of an earnings ledger is a coverage limitation, not a zero-dollar career.

## Current contract and history

The current section should keep the control status, present club, signing club, executed date, supported signing route, term coverage and source together. It must be possible to inspect the year-by-year schedule and supporting record without leaving the selected player.

History groups records by agreement, not by team stint or source file. Preserve the original signing identity when an ordinary trade changes the employer. Show the dated assignment beneath that agreement. A sign-and-trade has two linked events: the actual new signing and its assignment. Neither should be counted twice. An extension or amendment must identify the earlier agreement it changes so overlapping years are not added together as independent earnings.

Distinguish these evidence states:

- **Executed agreement recorded:** an actual signing record establishes the agreement and its known terms.
- **Existing contract, partial detail:** a dated control record establishes a contract but leaves some original terms unavailable.
- **Unverified continuity:** source evidence does not establish that an apparent salary row remains an active agreement.
- **Unsigned rights or open offer:** control or negotiations exist, but no executed contract is established.
- **Expired, waived, bought out or assigned:** a dated event explains the change; retain the prior record and relevant surviving obligations.

An accepted proposal is not automatically a registered contract. An unsigned option year is not another contract. A source correction should improve the appropriate agreement's evidence, preserve its identity and explain the correction; it should not manufacture another signing in the count.

## Options, free agency and dates

Show an option's holder, affected season, salary, sourced deadline, actual exercise decision and decision date separately. Before an outcome exists, preserve the conditional branch. Early termination provisions are distinct from options that add a season. Do not auto-exercise either type because a date has passed.

The ending year of a recorded salary fragment does not establish the agreement's true expiry. A projected exit status needs its conditions shown. Actual UFA/RFA classification follows the applicable contract, service, option and qualifying-offer records. An unsigned drafted rookie is neither UFA nor RFA merely because the tab needs a status label.

Use signing dates, effective dates and knowledge dates for their respective purposes. A future salary already fixed in a valid existing agreement may be displayed as a scheduled obligation. A later option choice, signing, guarantee amendment or trade outcome may not be revealed early. A missing publication date blocks a cap-derived percentage even if the raw historical cap file contains the number.

## Repository evidence and update discipline

The current career state supplies the display cutoff. Miami's `00_Team/Finances/contract_schedules.json` is authoritative for its simulated obligations. The June 26 league inventory supplies dated historical baseline evidence for other players; it must not overwrite simulated Miami outcomes. The tracked-player registry supplies identity resolution, not proof of a signed agreement.

The baseline is incomplete by design. Some veteran rows contain only remaining seasons or salary-pattern estimates; even a row labeled under contract may lack its original signing date, full term, guarantees or verified final year. Keep those limitations visible instead of promoting a schedule fragment to a complete original agreement.

### Shared catalog and dated maintenance records

`runtime/player_contracts.py` supplies `build_contract_catalog(root, player, clock=None)` and `contract_payload(profile, *, page, root)`. The shared catalog supports the protagonist's Contract tab and the `/contracts` directory of tracked-player pages. Stable player IDs, rather than a name-only match or display order, identify the selected player. Every tracked player has a destination even when the destination must explain incomplete contract coverage.

Additional executed agreements and source corrections belong in `career/<player>/Contracts/contract_records.json`. That owner directory can contain records for the other tracked players; each record identifies its subject explicitly. The document has `schema_version: 1` and a `records` array.

| Record field | Meaning |
| --- | --- |
| `record_id` | Unique identity of this source record |
| `recorded_on` | Date this recorded evidence becomes available to the career |
| `player_id`, `player` | Stable subject ID and attributed player name |
| `contract_id` | Stable agreement identity, retained across its amendments and assignments |
| `event` | `signed` for an executed agreement, `amended` for a change to an existing identified agreement, `assigned` for a reached transfer, or `recorded_existing` for preservation of sourced preexisting contract evidence |
| `contract` | Known terms and their supporting sources, using the fields below |
| `source` | Optional source path for the executed event or amendment, retained alongside the contract's supporting sources |
| `assignment` | For `assigned`, the actual `date`, `from_team`, `to_team` and source of the holder change |

The supported contract fields separate `signed_date`, `signing_team`, `original_term_seasons`, `start_season`, `end_season` and `expiry_date`. Financial records include `reported_total` with `amount` and `precision`; season-keyed `schedule`, `amount_kind`, `base_salary`, `cap_hit`, `guaranteed`, `likely_incentives` and `unlikely_incentives`; and an `options` list containing the affected `season`, option `type`, `amount`, `deadline`, `outcome` and `outcome_date`. Supporting detail includes `trade_clauses`, `free_agency`, `bird_rights` and `sources` containing repository paths or web URLs.

An amendment must identify an existing agreement. It is a partial overlay: supplied season-keyed financial fields update those seasons, while omitted fields retain the existing evidence. List fields such as `options` replace that list, so include the complete intended list when changing one option. Do not use an amendment to insert an unrelated contract under an old ID. Assignments also require existing contract evidence and preserve the signing date and original terms; an unknown original signing date stays unknown. A `recorded_existing` snapshot preserves an established agreement before its active ledger row changes or disappears. Its recording date does not become an invented signing date, and a further snapshot does not create another contract in history.

Both the record's knowledge date and a new agreement's signing date must have been reached before that signing enters the live view. Later outcomes within an agreement still retain their own date gates. Optional unsupported or unknown detail is left absent or explicitly unavailable according to validation; do not invent a value merely to fill a column. The workflow may preserve an `executed_terms` snapshot for an actual new signing; that original snapshot must not be replaced by a later remaining-salary fragment.

These records are an evidence-maintenance interface, not an alternative execution engine. Use an executed signing source for a new signed agreement, or an attributed source correction for an amendment. `runtime/contract_archive.py` preserves reached signing and assignment evidence from the normal execution writers. Changing a display record does not itself change the roster, cap ledger, eligibility, negotiation acceptance or career clock. Normal executed transaction workflows remain responsible for those changes.

Existing executed paths have different evidence:

| Existing path | Evidence the contract view can use | Important limitation |
| --- | --- | --- |
| `runtime.signing.sign_rookie` | Executed rookie-log entry, dated state/identity and written salary schedule | Guarantee protection is not established merely by `contract_salary` amounts |
| `runtime.signing.sign` | Negotiation signing record, written schedule, signing date, route and recorded guarantee amounts | Source identity must survive subsequent events; a current cap-sheet row is not the complete history by itself |
| `runtime.signing.apply_trade` | Dated executed assignment and the transferred contract's source terms | Preserve the original agreement; acquisition date is not signing date |
| `scripts/run_camp.py` | Actually executed camp contract, signed date, salary, recorded guarantee amount and guarantee deadline | An invitation or unsigned workout proposal does not establish this agreement |
| Historical league contract inventory | Existing known obligations with provenance and precision notes | Do not invent missing original seasons, dates, guarantees, option outcomes or renewal contracts |
| Player contract record maintenance | Explicit dated source corrections and newly recorded executed agreements | A document update records evidence; it does not authorize a signing or bypass the existing transaction workflow |

After a source change, the normal report rebuild must refresh the Contract tab, its Markdown fallback and every generated player-specific contract view. Validation should detect stale output or a broken source link. Generated pages are not the edit surface.

To maintain an existing record, update its owning dated source or add the supported amendment, then run:

```bash
python scripts/update_player_reports.py
python scripts/validate_repository.py
python -m unittest discover -s tests -q
```

Use `python scripts/update_player_reports.py --check` to verify generated freshness without writing. The website's record pages are read-only; there is no browser editor or separate contract-record CLI. Source changes reach the deployed views through the repository's established deployment workflow.

## Review cases

The implementation should be checked against an unsigned rookie, an executed rookie contract, a partial veteran schedule, a pending option, a recorded guarantee amendment, an ordinary trade, a sign-and-trade, a future-dated record and a tracked player without contract detail. Important assertions are that references never become signings, assignments do not duplicate value, original terms survive updates, unknown amounts remain unknown, and changing one player's source does not alter another player's contract history.

For the opening checkpoint, the expected Wade view is unsigned draft rights, no recorded signed professional agreement, and separately labeled draft/scale information. The reference site's later real-world career must never fill that empty history.
