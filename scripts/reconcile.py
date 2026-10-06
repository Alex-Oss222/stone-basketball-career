#!/usr/bin/env python3
"""Recompute every derived record from its sources, so a write in one place never leaves a stale copy elsewhere.

    python scripts/reconcile.py            rebuild what is stale, then validate
    python scripts/reconcile.py --check    report what is stale; write nothing (exit 1 if anything is)

The repository keeps two kinds of data. Source records are decisions and results (game results, contracts, option
decisions, trades, the register). Derived records are totals and views computed from them (Miami's schedule totals,
statistics pages, player and league cards, career views). A mismatch between the two is never a decision to make: the
derived copy is simply rebuilt. This script runs every builder in dependency order; each is idempotent and reads
sources only, so a run on a clean repository changes nothing. `scripts/advance.py` runs it before every validation,
so a writer that forgot a downstream refresh no longer stops the career. What validation still refuses after this is
a real conflict between source records, which needs a decision.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def schedule_totals(root, write):
    """Miami's contract schedule: season totals from its own entries (`signing.refresh_schedule_totals`)."""
    from runtime.seasons import active
    from runtime.signing import refresh_schedule_totals
    path = root / f"career/Dwyane_Wade/{active(root)}/00_Team/Finances/contract_schedules.json"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    sheet = json.loads(text)
    refresh_schedule_totals(sheet)
    new = json.dumps(sheet, indent=1, ensure_ascii=False) + "\n"
    if json.loads(new) == json.loads(text):
        return []
    if write:
        path.write_text(new, encoding="utf-8")
    return [path]


def run(script, *args):
    out = subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT, capture_output=True, text=True)
    return out.returncode, (out.stdout + out.stderr).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    changed = schedule_totals(ROOT, not args.check)
    if changed:
        stale.append("Miami schedule totals")
    print(f"Miami schedule totals: {'stale' if changed else 'current'}")
    for label, mode in (("results into notes, statistics pages, Miami and league cards", "scripts/write_back_results.py"),
                        ("career views", "scripts/update_player_reports.py")):
        code, out = run(mode, "--check") if args.check else run(mode, *(("--write",) if "write_back" in mode else ()))
        current = code == 0
        if not current:
            stale.append(label)
        print(f"{label}: {'current' if current else ('stale' if args.check else 'failed')}")
        if not current and not args.check:
            print(out[-2000:])
            return 1
    if args.check:
        return 1 if stale else 0
    code, out = run("scripts/validate_repository.py")
    print(out.splitlines()[-1] if out else "")
    if code:
        print("Validation still fails after rebuilding every derived record: the remaining problems are conflicts between "
              "source records, listed above, and need a decision.")
        print(out[-3000:])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
