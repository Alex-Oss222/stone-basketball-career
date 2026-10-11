---
type: phase
status: not_started
---

# Draft

## Player decisions
- 2005-10-31: Wade asks the scouting department to keep Kyle Lowry (Villanova, PG) and P.J. Tucker (Texas, F) under consideration for the 2006 draft, as recommendations, not demands. Weighed only on Miami's own picks. Records: `wade_requests.json` (`draft_prospect`), `../04_Training_Camp/Wade_Extension_Outlook_2005-10-31.md`.
- 2006-04-19: Wade asks Miami to draft P.J. Tucker (Texas, F) in the 2006 draft: "also tell them they better draft pj tucker". It replaces his 2005-10-31 evaluation request for Tucker and is weighed on Miami's own 2006 picks only, an engine-drawn decision by his standing, never a certainty. His standing keep_picks request (`../04_Training_Camp/wade_requests.json`) also weighs on every draft-night trade of a Miami pick. Records: `wade_requests.json` (`draft_prospect`, requested `draft`), runtime/draft.py rule 7.
- 2006-04-19: Under the user's premise (October 2026: "make it a hard rule") the standing keep_picks request (`../04_Training_Camp/wade_requests.json`) is a hard rule on draft night instead of a weighing: while it stands, Miami on the clock declines every trade-down offer without a draw and never moves up, and the draft record's `keep_picks` lists each declined call. The Tucker request is unchanged: it is weighed on Miami's own 2006 picks by his standing. Records: runtime/keep_picks.py, runtime/draft.py rule 6, docs/front_office.md (Keep the picks).

## Events

## Consequences
