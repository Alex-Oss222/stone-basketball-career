# Miami Heat | Finance desk

<!-- team-status:start -->

2005-06 through 2012-13 · AI/GM record · live position from [finance.json](finance.json) (as of 2005-12-19), shown on 2005-12-24

Counted salary $65,714,782 against the published $49,500,000 cap: cap room -$16,214,782 (regular season). Tax threshold: not published at this date. Contract guarantee review: 2006-01-07 keep-or-waive, 2006-01-10 kept contracts guaranteed.

<!-- team-status:end -->

[Open the cap sheet](cap_sheet.md) · [Team hub](../README.md) · [Career checkpoint](../../current_state.json)

## Files

| Record | What it answers |
| --- | --- |
| [Cap sheet](cap_sheet.md) | All 17 player rows across eight seasons, with totals, option markers and payroll notes |
| [Live finance state](finance.json) | Which amounts and decisions are usable at the current career date? |
| [Contract schedules](contract_schedules.json) | Which player, season, contract term and source produce each subtotal? |
| [Cap archive](league_cap_history.json) | What were the later historical league caps, and when may each become live? |

## Reading the numbers

The main table uses source dollar amounts, with one player per row and one season per column. Player names link to their cards. Salary, draft-hold and priced-option subtotals sit beneath the players; contract notes follow the table.

- **Salary** is an existing contract amount, including any unprotected portion until an actual waiver. It is not a guarantee total. **PO, TO and ETO** mark conditional years; the projection separates them from the base.
- **H** marks the unsigned first-round hold. **DR** marks unsigned second-round rights, and **FA** marks a projected free-agent hold if expiring rights are retained. **G** marks amended guarantee terms. **≈** marks a rounded report and every affected subtotal. Holds are cap allocations, not cash spending.
- A **dash** means no player amount is scheduled for that year. **Zero** is a known subtotal with no scheduled dollars. **? / null** means unresolved, including future total team salary and cap room.
- **Cap room** requires a published limit and a complete reconciliation. Tax payroll and any tax bill require their own accounting.

The eight-season view rolls forward existing obligations. It does not assume later signings or use later Miami transactions. Historical cap actuals sit in a separate archive; they are not June 2003 forecasts. The rules in force are the 1999 CBA, without modern apron accounting.

## Updating the records

1. Record the dated transaction or option decision in its owning career note.
2. Update the player's term and amount type in `contract_schedules.json`. Replace an unsigned hold when a contract is executed; do not count both.
3. Recompute base salary, draft holds and conditional subtotals for all eight seasons. Keep unpriced items unresolved.
4. Reconcile free-agent holds, roster charges, exceptions and other adjustments in `finance.json` before publishing usable room.
5. Refresh `cap_sheet.md`, then run repository validation and tests.

## Research basis

The contract audit compares contemporary salary reports with contract histories and the [original 1999 NBA/NBPA agreement](https://ipmall.law.unh.edu/sites/default/files/hosted_resources/SportsEntLaw_Institute/1999NBA_NBPA_CBA.pdf). Sources, calculations and conflicts remain beside each record. The [cap sheet](cap_sheet.md#sources-and-maintenance) links the key evidence.

The audit corrects Johnson to a pending team option, prices all three minimum-contract options, restores Ellis’s existing final year, and aligns Jones’s and Grant’s roster terms with their contracts. Ellis’s exact salary and guarantee rider, the minimum deals’ protected amounts, and House’s conflicting salary reports remain explicit gaps. No subsequent option exercise, waiver, signing or trade is imported.

The supplied payroll references continue to determine the layout: player rows, eight season columns, subtotals below, then contract notes. The directory and file structure are unchanged.
