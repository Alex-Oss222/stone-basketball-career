#!/usr/bin/env python3
"""Contract extensions for every club on their days (`runtime/extensions.py`).

    python scripts/extension_day.py --write 2005-10-31     decide every extension day up to the date not yet decided,
                                                          write the engine packets and Wade's offer, apply drawn or
                                                          answered outcomes to the contracts
    python scripts/extension_day.py --eligible 2005-10-31  read-only: the players eligible that day, and why the other
                                                          final-season contracts are not

Idempotent: a day is decided once in `<season>/League/extension_decisions.json`, on its own date (the career clock on
it); draw packets with `python scripts/draw_decisions.py`, then run again to apply them. Wade's offer (a clear one at
once, a close call once the engine draws Miami's offer) waits for his reply (`scripts/player_milestone.py --reply`, kind
`extension`); run again after it. Evidence is dated on each day. A day the clock passed without deciding it, a day ahead
of the clock, or a day behind an unresolved earlier decision is refused: the step prints "extensions refused: ..." and
exits 1, so the driver stops with the reason on screen (a missed day needs a decision, never a late run).
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import extensions  # noqa: E402


def money(v):
    return f"${v:,}"


def describe(d):
    o = d.get("offer")
    head = f"{d['day']}  {d['club']}: {d['player']} {d['kind'].replace('_', ' ')} extension"
    if d["outcome"] == "no_offer" and not o:
        return f"{head} -> no offer ({d['club_call']['how']})"
    terms = f"{o['years']} seasons from {o['first_season']}, {money(o['first_salary'])} rising {money(o['raise'])} ({money(o['total'])})"
    if d["wade"] and d["club_call"]["decision"] == "draw":
        return f"{head} -> close call: Miami's offer of {terms} is an engine draw ({d['packet']}); Wade answers an offer"
    if d["wade"]:
        return f"{head} -> offer of {terms}, waiting on Wade"
    how = "club call and answer drawn together" if d["club_call"]["decision"] == "draw" else "his answer is an engine draw"
    return f"{head} -> offer of {terms}; {how} ({d['packet']})"


def applied_lines(applied):
    out = []
    by_id = {}
    for path in sorted((ROOT / extensions.PLAYER).glob("*/League/extension_decisions.json")):
        by_id.update({d["id"]: d for d in extensions._read(path)["decisions"]})
    for i in applied:
        d = by_id[i]
        o = d.get("offer")
        if d["outcome"] == "signed":
            prefix = "WADE EXTENSION" if d["wade"] else "MIAMI EXTENSION" if d["club"] == extensions.MIAMI else "EXTENSION"
            out.append(f"{prefix} {d['club']}: {d['player']} {o['years']} seasons from {o['first_season']} ({money(o['total'])})")
        elif o:
            declined = d["outcome"] == "declined"
            what = "declines" if declined else "is not offered (the drawn club call)"
            line = f"{d['club']}: {d['player']} {what} the {o['years']}-season extension ({money(o['total'])})"
            label = "EXTENSION DECLINED " if declined else "EXTENSION NOT OFFERED "
            out.append(("WADE " if d["wade"] else "MIAMI " if d["club"] == extensions.MIAMI else "") + label + line)
    return out


def main(argv):
    if len(argv) != 3 or argv[1] not in ("--write", "--eligible"):
        raise SystemExit(__doc__)
    day = argv[2]
    if argv[1] == "--eligible":
        eligible, skipped = extensions.eligibility(day, ROOT)
        for c in eligible:
            print(f"ELIGIBLE {c['club']}: {c['player']} ({money(c['last_salary'])} in {c['final_season']}) - {c['eligibility']}")
        for player, club, reason in skipped:
            print(f"not eligible {club}: {player} - {reason}")
        print(f"extensions on {day}: {len(eligible)} eligible, {len(skipped)} final-season contracts not eligible")
        return
    try:
        decided, written, applied, waiting = extensions.run(day, ROOT)
    except extensions.ExtensionError as e:
        print(f"extensions refused: {e}")
        raise SystemExit(1)
    for d in decided:
        print(describe(d))
    for line in applied_lines(applied):
        print(line)
    for oid in waiting:                                 # every open offer, a clear one or Miami's drawn close call
        for path in sorted((ROOT / extensions.PLAYER).glob(f"*/01_Free_Agency/Wade_Extension/{oid}.json")):
            r = extensions._read(path)
            o = r["offer"]
            print(f"WADE EXTENSION OFFER {r['club']}: {o['years']} seasons from {o['first_season']}, {money(o['first_salary'])} "
                  f"rising {money(o['raise'])} ({money(o['total'])}); answer with scripts/player_milestone.py --reply "
                  f"(kind extension, {path.relative_to(ROOT).as_posix()})")
    print(f"extensions: {len(decided)} decided, {len(written)} draw packet(s) written, {len(applied)} applied, "
          f"{len(waiting)} waiting on Wade")


if __name__ == "__main__":
    main(sys.argv)
