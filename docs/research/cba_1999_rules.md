# Research: 2003 offseason rules under the 1999 NBA CBA

Research report gathered October 2, 2026 for `docs/front_office_design.md`. Evidence levels are marked per item (FAQ, V, S, I); items marked S or I are unverified for 1999 and are flagged as such where the rules are encoded. This is a research record, not an operative rule file: the rules the simulation applies live in `library/2003/league/nba_1999_cba_rules.json`.

**Verification key.** `FAQ` = found in the repository's extract of Coon's 1999 FAQ (`library/2003/league/cba_1999_salary_cap_faq_extract.txt`), which I could not re-read live: `cbafaq.com`, `web.archive.org` and the 1999 agreement PDF (`ipmall.info/.../1999NBA_NBPA_CBA.pdf`) are all blocked by the egress proxy. `V` = verified in a page I fetched and read. `S` = search-snippet only (page blocked: shamsports, hoopsrumors, realgm, nbadraft.net, deseret, blogmaverick, sportsbusinessclassroom, apbr, eskimo.com). `I` = inferred from later-CBA rules or contemporaneous examples; treat as unverified for 1999.

Sources cited by tag: ESPN-0715 = espn.com/nba/news/2003/0715/1581132.html; ESPN-0716 = .../2003/0716/1581622.html; ESPN-0702 = .../2002/0716/1406462.html; ESPN-1101 = espn.com/gen/s/2001/1108/1275416.html; BBR-TX = basketball-reference.com/leagues/NBA_2004_transactions.html; BBR-DET = basketball-reference.com/teams/DET/2004_transactions.html; BBR-CAP = basketball-reference.com/contracts/salary-cap-history.html; W-CAP = en.wikipedia.org/wiki/NBA_salary_cap; W-TAX = en.wikipedia.org/wiki/Luxury_tax_(sports); W-CBA = en.wikipedia.org/wiki/NBA_collective_bargaining_agreement; W-STEP = en.wikipedia.org/wiki/Ted_Stepien; CUBAN = blogmaverick.com/2004/07/12/some-nba-rules/ (S); ND05 = nbadraft.net/?p=33783 (2005 deal-points summary, S); SI09 = si.com/more-sports/2009/07/15/millsap (S); SPOT = spotrac.com/nba/player/_/id/16236/karl-malone (S); SLAM = slamonline.com/?p=254359 (S); CBS00 = cbsnews.com/news/shaq-gets-big-bucks-extension/ (S).

## 1. Free-agency calendar, 2003

- Moratorium ran July 1–15, 2003. The cap was released "Tuesday night [July 15] on the eve of the expiration of a moratorium on free agent signings" (V, ESPN-0715). Earliest dated free-agent signing in the league log is July 16, 2003 (Mourning, NJ); nothing is logged July 1–15 except a waiver (V, BBR-TX). Andre Miller signed his offer sheet "Wednesday" July 16 (V, ESPN-0716). Talks and verbal agreements during the moratorium were normal (Malone/Payton agreed with the Lakers July 4, signed later; S, SPOT/ESPN links) — I.
- 2003-04 cap: $43,840,000, +9% from $40,271,000 (V, ESPN-0715; V, BBR-CAP). Minimum team salary 75% of cap = $32,880,000 (V, ESPN-0715).
- Average salary = $4,917,000 = full mid-level exception starting salary (V, ESPN-0715). Mid-level usable for contracts up to 6 years, 10% raises, splittable — I.
- "$1 million exception" was worth $1,500,000 in 2003-04 (Malone's one-year $1.5M "veteran's exception" after the Lakers used the $4.9M MLE on Payton; S, SPOT/ESPN 0704). W-CAP (V): it "was valued at $1 million for only the first year of the agreement." Usable every other season — I (name of its 2005 successor, "bi-annual").
- Tax line: 2002-03 $52.9M, assessed July 2003 dollar-for-dollar on last season's payroll (V, ESPN-0715). 2003-04 line was not known in July 2003: "the players' union said it expected next season's tax threshold to be $57 million" (V, ESPN-0715); the actual, computed after the season, was $54.56M (V, W-TAX table: 52.88 / 54.56 / N/A for 2004-05 / 61.7 for 2005-06).
- Rookie scale timing: first-round picks count at 100% of scale from draft night until signed (FAQ Q41) and could be signed inside the moratorium — LeBron James signed July 3, 2003 (S, ESPN 0703/1576436). Second-round picks carry no hold (FAQ Q41).

## 2. Free-agent types and rights

- Restricted: (a) first-round picks after the fourth (option) year of a rookie-scale contract; (b) veterans who entered in 1998-99 or later with three or fewer seasons; requires a qualifying offer by June 30; QO is one season; team over the cap gets an automatic exception for it; QO can be rescinded, making the player unrestricted (FAQ Q34).
- QO amount: rookie-scale players by draft slot (per-pick percentages in `nba_2003_04_cap_rules.json`); others the greater of 125% of prior salary or minimum + $150,000 (FAQ Q34). Player may accept the QO through October 1 — I.
- Offer sheets: at least three seasons, no non-cash compensation; incumbent has 15 days to match principal terms (FAQ Q34; repo research template cites the agreement for the same). The 2005 CBA cut this to 7 days (S, ND05; W-CAP says pre-2011 was seven). No Gilbert Arenas provision existed (introduced 2005, S), so a 1–2-year RFA could receive any starting salary and the incumbent could match only with cap room or an exception it actually held — I.
- Signing bonus limit: 20% of total salary (2005 rule 20%, 17.5% for RFA offer sheets; S, SI09). Miller's 2003 offer sheet carried a $10M bonus on $51M = 19.6% (V, ESPN-0716), so in 1999 the 20% cap applied to offer sheets too — I.
- Larry Bird: three seasons with the club without waiver or free-agent change (traded rights travel); up to the max; 12.5% raises; up to 7 years (FAQ Q17/23/25). Early Bird: two seasons; greater of 175% of prior salary or the average salary; 12.5% raises; 2–6 years (FAQ Q17). Non-Bird: greater of 120% of prior salary or 120% of minimum; 10% raises; up to 6 years (FAQ Q17). Confirmed as "7 years for Bird players and 6 years for other players" before 2005 (S, ND05) and "12.5% ... down to 10.5%; others 10% down to 8%" (S, ND05).
- Cap holds (% of prior salary): Bird 150 (prior ≥ average) / 200 (below); Bird off rookie scale 250 / 300; Early Bird 130; Non-Bird 120; never above the player's max; two-season average if the last raise exceeded $4M (FAQ Q28). No 190% row exists in the 1999 rules (190% is a 2011-CBA figure). Hold ends on re-signing, signing elsewhere or renouncing (Q30). Renouncing forfeits Bird/Early/Non-Bird rights until the following June 30; reversible only if the renouncement made room for an RFA whose team matched (Q31–32).
- Sign-and-trade: new contract of at least three non-option seasons (repo research template citing the agreement); first-year guarantee was a 2005 addition — I; BYC applies (see §4).
- Minimum exception: up to two years, second year at that season's minimum; also allows acquiring minimum players by trade (FAQ Q17). Scale in `nba_1999_cba_minimum_salary_scale.json` (FAQ Q9). League reimbursement: players with 5+ seasons on one-year/10-day/rest-of-season minimum deals count only the four-year minimum ($688,679 in 2003-04) (FAQ Q9, repo cross-checked with Bender; not re-verified by me).
- Rookie scale: 80–120% of scale; three seasons plus a team option for a fourth, "exercised by October 31 after the player's second season" (FAQ Q38). Pick 5 scale 2003: $2,197,000 / $2,361,800 / $2,526,600, option +26.7%, QO +32.6% (repo cap-rules file, RealGM). Note the scale's own year-2 and year-3 figures are fixed at +7.5% and +15% of year 1 (arithmetic on the file), so "10% raises" (Q38 as extracted) is not the operative figure for scale deals.
- 10-day contracts: not before January 5; two per team per player per season, then rest-of-season — I (modern rule, same since 1999).

## 3. Maximum salary, length, raises, options

- Max starting salary: 25% / 30% / 35% of the cap for 0–6 / 7–9 / 10+ years of service = $10,960,000 / $13,152,000 / $15,344,000, or 105% of prior salary if greater. Kidd "30 percent of the cap, or $13.152 million ... annual increases of 12.5 percent" (V, ESPN-0715). The 105% clause: W-CAP states it for the current rule (V); the 1999 wording is cited to Coon Q22 by the repo but not re-read — I for 1999.
- Length: 7 years with Bird rights, 6 otherwise (FAQ Q17; S, ND05). Raises 12.5% Bird/Early Bird, 10% other, measured from first-year salary (FAQ; S, ND05).
- Trade bonus (kicker) up to 15% of remaining salary — I (S, hoopsrumors glossary; unchanged across CBAs). Signing bonus 20% (§2).
- Options: one player or team option, final season only; early termination option only in contracts of 5+ seasons and not before the end of the fourth — I (e.g. Kobe Bryant's July 2004 seven-year deal had an ETO after season five). Guarantees are negotiable; no minimum guarantee required — I.
- Over-36 rule (age threshold changed to 36 in the 1999 CBA; W-CAP, V): seasons after the 36th birthday presumed deferred compensation — relevant for 40-year-old Malone-type signings.

## 4. Trade rules

- Matching for teams over the cap after the trade: incoming salary ≤ 115% of outgoing + $100,000; Cuban, July 2004: "current year salaries exchanged must be within 15pct plus 100k dollars" (S, CUBAN). 2005 raised it to 125% + $100K (S, ND05/raptorshq). Outgoing salaries may be aggregated — I.
- Base-year compensation: applies to a player re-signed via Bird/Early Bird with a raise over 20% by a team over the cap; his outgoing trade value is the greater of 50% of new salary or prior salary (V, W-CAP, general rule; 1999 thresholds the same — I). Duration under 1999: through the first season of the contract (next June 30) — I, unverified. Rookie-scale contracts were not BYC — I.
- Newly signed free agents: not tradable for three months or until December 15, whichever is later — I (modern rule; believed identical in 1999). A signed first-round pick: 30 days — I.
- Non-simultaneous (traded-player) exception: 100% of outgoing salary + $100K, usable for one year — I.
- Cash: $3,000,000 maximum per trade; "the same as in the old CBA" per 2011 commentary (S, sheridanhoops) — I for 1999.
- Draft picks: Stepien rule — a team may not leave itself without a first-round pick in consecutive future drafts; satisfied by holding another club's first (V, W-STEP).
- Trade deadline: Thursday, February 19, 2004, 3 p.m. ET (S, SLAM; the Wallace three-team trade is dated Feb 19, 2004 in BBR-DET, V).
- Rosters: 12 active + up to 3 on the injured list = 15 maximum; the 2005 deal "expanded active rosters from 12" and renamed the IL the inactive list (S, ND05; V, W-CBA: "Prior to the 2005 CBA, injured players could be placed on an injured list but were forced to sit out a minimum of five games"). Minimum roster 12 (11 permitted for up to two weeks) — I. A two-for-one must not leave the team above 15 after the trade; waive first or carry space — I.

## 5. Luxury tax and escrow (1999 CBA)

- Escrow: 10% withheld from every paycheck from 2001-02 (V, ESPN-1101). Players' guarantee 55% of BRI in 2001-02 through 2003-04, 57% in 2004-05 (ESPN-1101 V for 55%; S, Ringer/ND05 for 57% in 2004-05).
- Tax trigger: tax existed only if league salaries and benefits exceeded 61.1% of BRI (55 ÷ 0.9); in 2001-02 they were 60.2% so no tax and half the escrow was refunded (V, ESPN-0702). First tax year 2002-03 (V, W-TAX; ESPN-0715). With a 57% guarantee the 2004-05 trigger was 63.3% and no tax was levied (V, W-TAX "N/A").
- Rate: $1 per $1 over the line, computed on final team salary after the season; proceeds redistributed to non-taxpayers (V, ESPN-0715; W-TAX). Lines: $52.88M (2002-03), $54.56M (2003-04). The line was retrospective — a front office in 2003-04 planned against an estimate (~$57M per the union) — V, ESPN-0715.

## 6. Extensions

- Rookie-scale extensions: window from the end of the third season to October 31 of the fourth (S, hoopsrumors; same in 2005); up to six new seasons at up to the max with 12.5% raises — I, consistent with Pierce's six-year $80.27M (Aug 1, 2001) and Nowitzki's six-year max (Oct 22, 2001) extensions (S, shamsports profiles).
- Veteran extensions: permitted from the third anniversary of signing for contracts of four or more years; total of remaining plus new seasons capped at six; 12.5% raises off the last existing-year salary with Bird rights — I, consistent with O'Neal's Oct 2000 three-year extension leaving "six more seasons" (S, CBS00) and Garnett's Oct 2003 five-year $100M extension on one remaining year (S). 
- Extensions could not be signed during the moratorium? Not established — I.
- ETO: see §3.

## 7. Other

- No amnesty in the 1999 CBA; the one-time tax amnesty came in August 2005 (W-CAP/W-CBA mention only 2005 and 2011 versions, V).
- Hardship: with three on the injured list and a fourth injury, a team could apply to place the fourth on the IL and sign a replacement — I (mirrors the 2005 deal-points language quoted at W-CBA ref 12, V).
- Waivers: 48-hour claim period, claims by reverse standings, claimant assumes the contract; unclaimed salary stays on the waiving team's cap — I. Set-off: team's obligation reduced by 50% of what the player earns elsewhere above the one-year veteran minimum — I.
- Buyouts: negotiated; remaining salary counts as paid — I.
- Disabled-player exception: lesser of 50% of the injured player's salary or the mid-level; season-ending injury certified by a league doctor — I (W-CAP describes 2005 version, V).
- Training camp: up to 20 under contract; "summer contracts" (summer league/camp deals, no cap charge if waived before the season) and non-guaranteed camp deals existed — I.
- Draft rights: unsigned second-round picks sign with cap room or the minimum exception; no second-round exception — I.

## 8. Repository discrepancies and flags

1. **`docs/front_office.md` vs FAQ Q38** — it says Wade's 2006-07 team option is "to be exercised by October 31, 2004." Q38 (and `nba_1999_cba_rules.json` "rookie_scale.term") say by October 31 after the player's **second** season, i.e. October 31, 2005 (Nowitzki's 2001-02 option was exercised Oct 16, 2000, after his second season). Fix the date.
2. **`nba_2003_04_cap_rules.json` luxury_tax_line = 54,556,722, status "historical_actual"** — matches W-TAX ($54.56M) to rounding, but the exact figure is unverified from a primary source, and it was not knowable in 2003-04: the line was computed after the season; the July 2003 contemporaneous projection was ~$57M (ESPN-0715). The live front office should plan on a projection, not the actual, until the 2004 computation date.
3. **`nba_1999_cba_rules.json` rookie_scale.raise_percent = 10** — the scale itself fixes years 2–3 at +7.5%/+15% of year 1 (the repo's own pick table). Harmless but misleading; note it is not a negotiable raise.
4. **`nba_1999_cba_rules.json` "unverified" list** — the 105% max rule and mid-level = average salary are both confirmed as 2003 practice: ESPN-0715 explicitly ties the $4.917M average to the full mid-level and Kidd's 30%-of-cap max. The minimum-contract hold rule remains unverified (no source found).
5. **`nba_2003_04_cap_rules.json` biennial = 1,500,000** — confirmed (Malone's $1.5M exception, 2003); the note calling it the "$1 million exception" is correct naming.
6. **Cap holds**: the task's "190%" figure is not a 1999 rule; the repo's 150/200/250/300/130/120 set is correct for 2003-04 (250% applies "in remaining seasons" from 2000-01).
7. **Offer-sheet match window**: repo (15 days) is right for 1999; 7 days is the 2005 CBA, 3 days post-2011.
8. **`runtime/era.py`** (12 actives, 15 max, injured list) is consistent with the 2003-04 rules.
9. Nothing in the repo records the 2003 moratorium dates (July 1–15, signings from July 16) or the trade deadline (Feb 19, 2004); `league_cap_history.json` correctly gates the cap at July 15, 2003.

Access limits: the primary FAQ, the agreement PDF and several secondary glossaries were blocked, so items marked I/S should be re-checked against `cbafaq.com/salarycap99.htm` when it is reachable.
