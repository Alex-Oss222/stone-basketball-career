# ADR 0002: Calendar accessibility semantics

- Status: Accepted
- Date: 2026-07-16

## Context

An ARIA grid requires a complete keyboard interaction model. Adding
`role="grid"` without roving focus, directional navigation, Home/End behavior,
and reliable focus management would replace useful native semantics with an
incomplete custom widget.

## Decision

Render every month as a descriptively headed `<section>` containing a semantic
`<table>`. Each table has a caption, weekday headers with `scope="col"`, and
ordinary cells. Selectable dates use native `<button>` elements. Native tab
order remains available; visible focus styles are required.

Selected date, stored current date, managed-team participation, TBA state, and
game status use explicit text or accessible names and never color alone.
Canonical `LocalDate` strings remain in `<time dateTime>` attributes while
visible dates use deterministic project formatting.

The calendar must not use `role="grid"` unless a later ADR approves and tests a
complete grid keyboard model. Responsive layouts may allow a table region to
scroll or provide an equivalent semantic agenda presentation, but must retain
headings, labels, reading order, and keyboard access.

The current fixed-English interface uses a documented, deterministic weekday
order rather than host locale. Milestone 2 uses Sunday through Saturday.

## Compatibility and consequences

- Existing navigation IDs, skip link, focus indicators, captions, and scoped
  header conventions remain intact.
- Native table and button behavior is simpler and more robust, though tabbing
  through many interactive dates is less compact than a fully implemented
  application grid.
- Accessibility tests must assert semantics and the absence of an unsupported
  grid role; keyboard and narrow-window behavior also require manual checks.

## Non-goals

This ADR does not introduce a calendar library, locale service, or custom
screen-reader widget.
