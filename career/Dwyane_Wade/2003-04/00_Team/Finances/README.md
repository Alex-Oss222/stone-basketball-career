# Miami Heat | Finance desk

June 26, 2003 · 2003-04 through 2010-11 · AI/GM record

[Open the cap sheet](cap_sheet.md) · [Team hub](../README.md) · [Career checkpoint](../../current_state.json)

The cap sheet starts with $26,269,078 in signed salary schedules and Wade's $2,197,000 unsigned draft hold. Their $28,466,078 subtotal is not complete team salary. Options, holds and other charges still need reconciliation, and the next season's cap is unpublished at this checkpoint.

## Files

| Record | What it answers |
| --- | --- |
| [Cap sheet](cap_sheet.md) | All 17 player rows across eight seasons, with totals, option markers and payroll notes |
| [Live finance state](finance.json) | Which amounts and decisions are usable at the current career date? |
| [Contract schedules](contract_schedules.json) | Which player, season, contract term and source produce each subtotal? |
| [Cap archive](league_cap_history.json) | What were the later historical league caps, and when may each become live? |

## Reading the numbers

The main table uses exact dollars, with one player per row and one season per column. Player names link to their cards. Salary, draft-hold and priced-option subtotals sit beneath the players; contract notes follow the table.

- **Salary** is an existing contract amount. **PO, TO and ETO** mark conditional years; the projection separates them from the base.
- **H** marks the unsigned first-round hold. **DR** marks unsigned second-round rights, and **FA** marks a free-agent hold requiring review. Holds are cap allocations, not cash spending.
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

The supplied payroll screenshots informed the player-by-season matrix, inline option markers, totals and contract notes. [Spotrac's multi-year layout](https://www.spotrac.com/nba/los-angeles-lakers/yearly) provides a further reference. [The 1999 CBA FAQ](https://www.cbafaq.com/salarycap99.htm) supplies era-specific accounting context. Individual contract sources remain beside their terms. [The NBA's 2010 cap announcement](https://pr.nba.com/nba-salary-cap-for-2010-11-season-set-at-58-044-million/) supports the two added archive seasons. Source gaps remain named on the cap sheet.
