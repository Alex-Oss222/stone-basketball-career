# Archive — historical, not current

Nothing in this folder is current. These documents are kept because they record
how decisions were reached, not what is true now.

**Do not cite anything here as status. Do not plan from it.** The single
authoritative plan is [`../ROADMAP.md`](../ROADMAP.md).

Every file here contains statements that were true when written and are false
now. Some examples, so this is concrete rather than a vague warning:

- `SCHEDULE_FOUNDATION_ROADMAP.md` claims "rotation validation already exists."
  It never did — there is no `RotationPlan`, rotation generator, or rotation
  validator in the tree. Building it is §8 of the roadmap. This single false
  sentence is the reason this archive exists: it survived long enough to be
  planned against.
- It also frames the next step as "decide the V3 result shape first." That was
  superseded — the save format collapses to one version with no migrations
  (§7), so the result shape is now *learned by building the box score screen*
  (§6), not designed up front.
- `MILESTONE_2_CALENDAR_IMPLEMENTATION_PLAN.md` is a delivery plan for work that
  shipped. Its "planned" sections read as future tense but are done.
- `CALENDAR_CONTRACT_AUDIT.md` is a point-in-time audit whose header says
  "Status: Complete" — meaning the *audit* finished, not the work. Four of the
  five gaps it identifies have since shipped, so its "there is no X" claims are
  now wrong in a way that is easy to act on by mistake.

## Why these were archived

They were peer planning documents with overlapping scope and a precedence order
you had to reconstruct from banners — `ROADMAP` deferred to
`SCHEDULE_FOUNDATION_ROADMAP`, which deferred to `MILESTONE_3`, which contested
`MILESTONE_2`'s frozen contracts. Four documents, no single source of truth.
That is how a false claim went unnoticed.

There is now one plan, one pointer, and a set of clearly-labelled reference
specs. If you find yourself wanting to add a fifth planning document, add a
section to `ROADMAP.md` instead.
