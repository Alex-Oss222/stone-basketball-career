# Team state

This folder is AI/GM controlled. The user does not directly edit its basketball decisions.

Only the minimum team state needed for a player career and game simulation is kept here:

- `team_config.json`: team identity and tactical configuration
- `Team/roster.json`: controlled roster
- `Team/rotation.json`: current playing rotation and minute targets
- `Team/Player_Cards`: reusable basketball player-card format and eventual team player cards
- `Finances/finance.json`: current team cap/tax and contract state

Do not add coaching-office, film-library, scouting-library, archive, or organization-payroll systems unless a later simulation requirement actually needs them.
