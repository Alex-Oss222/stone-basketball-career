Every finding in group A is fixed. Reconcile ends clean, the two `--check` runs pass, and the branch is committed and not pushed.

**Findings**
- **wade-stats/WADE-STATS-01: fixed.** Wade's agreement now has the option row `2006-07 | team_option | $3,201,202 | 2005-10-31 | exercised | 2005-10-31`, in `Contract.md`, the card data and both contract pages. The catalog reads the sheet's `team_option_season` and `fourth_year_option_deadline` and lays the applied decision from `option_decisions.json` over it.
- **cards-contracts/F7: fixed.** All 58 recorded decisions now show their outcome and date. A declined option, opt-out or exercised early termination ends the agreement the season before, so Nachbar, Ely, Tskitishvili and Redd no longer keep an old contract open. The 24 players from the 2003 draft class had no agreement at all; they now get one from the league contract ledger (`League/contracts.json`).
- **cards-contracts/F4: fixed.** The catalog now applies, in date order, the league moves, summer and Miami trades, the expansion draft, and the real trades and waivers before the symmetric league. Trades and claims are assignments; 10-day and rest-of-season deals are new agreements; waive, clear, expire and retire close the agreement on their date, and a claim reopens it. Zero registry players now have a current contract at a club other than `club_truth.holder`, and none who cleared waivers or expired still shows a current contract. One edge remains: Ronnie Price signed a 10-day with Toronto on 2006-04-19 and no expire move was ever written. The holder keeps him at Toronto, but his contract has expired, so his page says "rostered; no contract in force in the dated records". The missing move is in the league market's records, not the catalog.
- **cards-contracts/F5: fixed.** `roster_moves.waive` and `scripts/guarantee_review.py` now use a new helper, `contract_archive.signed_record`, which picks the signing with the sheet entry's date, else the latest. The misfiled record in `contract_records.json` now names `jonesju01-2005-10-04` (record id and contract id) and carries a correction note; his 2003 agreement stays voided on 2003-10-27.
- **cards-contracts/F6: fixed.** An agreement's club is now its latest-dated assignment. Eddie Jones shows Miami and Lamond Murray shows Utah.
- **cards-contracts/F8: fixed.** Agreements from Miami's sheet and archive end at their last scheduled season, so none of the six stays current.
- **cards-contracts/F9: fixed.** A missing amount now counts as unknown when matching records. To avoid false merges, two records with no amount on both sides only match when one has just a signing date and the other just a contract id. P.J. Brown is one agreement at $8.5M.
- **cards-contracts/F10: fixed.** The register's "signs with" club now applies only to players with no dated club; the five players match `club_on`.
- **ages-identity/ID-04: fixed.** Status now comes from the agreement in force on the cutoff. An agreement past its expiry reads "expired". With none in force, the status reads "unsigned free agent (…)", "out of the league (…)" or "rostered; no contract in force in the dated records". 14 players whose real careers ended while a club still owes them read "out of the league (contract on the books)".
- **ages-identity/ID-07: fixed.** The page refresh deletes contract pages whose id left the catalog, and `update_player_reports.py --check` reports any left on disk. The four orphan files are gone.

**Forward-only gates:** none needed, so none added. Nothing that decides anything reads the contract catalog: only the contract pages and Wade's card read it. The only reader of the corrected release record is the catalog itself; `league_cards.signings` and the extension check read only `signed` records. The waive and guarantee-review change only affects which contract id future archive records name. I did not change `runtime/options.py`: its open-option reader uses `amount_kind`, so changing what it writes would reopen exercised options in decision paths. The catalog reads the decision records instead.

**Commits**
- Source: `056970aac6c` (archive helper, waive and guarantee-review lookup, record correction)
- Source: `301d1c04b9d` (catalog, page pruning, docs, `tests/test_audit_a.py`)
- Regenerate: `c69d230ebcb` (1320 files)

**Tests (python3.12, one module at a time):** `test_audit_a` 15 OK (all 15 fail on the original code), `test_player_contracts` 28 OK, `test_contract_pages` 5 OK, `test_contract_realism` 5 OK, `test_extensions` 64 OK (it first exposed a crash when no cutoff is passed, now fixed), `test_contract_archive` + `test_roster_moves` 16 OK (1 skipped), `test_identity_contract` 8 OK, `test_view_independence` 1 OK, `test_live_player_cards` 21 OK, `test_season_change` 14 OK.

**Reconcile, last lines:**
```
results into notes, statistics pages, Miami and league cards: current
career views: current
Repository validation passed.
```
`update_player_reports.py --check` says "Detailed career views are current."; `build_league_cards.py --check` says "League cards match the dated records."

**Risks for the integrator**
- **Likely conflicts:** all 1310 pages under `career/Dwyane_Wade/Contracts/players`, plus `Contracts/{README.md,catalog.json,index.html}`. Wade's `Stats_and_Awards/{Contract.md,player_cards.html,player_cards_data.json}` will conflict if group D regenerates them. Code files others may touch: `runtime/player_reports.py` (`report_errors`) and `scripts/refresh_career_views.py`. Re-run reconcile after merging rather than resolving page conflicts by hand.
- **New inputs:** the catalog now reads `League/league_moves.json`, `option_decisions.json`, `League/contracts.json`, `09_Draft/expansion_*.json` and the library's real trades and waivers. If another group changed any of these, contract pages will shift on regeneration.
- **Status wording:** the directory's status filter values have changed.
- **Not touched:** Eddie Jones's history shows a 2005-01-31 Utah→Houston league trade, but the 2005 summer trade back to Miami says "from Utah". The two source records disagree; I left them alone.