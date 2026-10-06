#!/usr/bin/env python3
"""Advance the career day by day until a target date, stopping whenever Wade has a decision to make.

    python scripts/advance.py --to 2004-04-14

Each day runs the dated systems in order, each idempotent, so a stopped day can simply be run again:
  1. the clock moves to the day; the January 7 and 10 guarantee steps run on their dates;
  2. a due fortnightly staff rotation review is written, its close starting battles drawn by the engine, and
     the review completed;
  3. the league's market day (waivers, claims, 10-day contracts) and, on Mondays to the deadline, the trade scan,
     its packets drawn and accepted deals executed; then Miami's own trade step (`scripts/run_trade.py --season-day`:
     Mondays from December 15 to the deadline, one proposal at a time, drawn by the engine); disturbed clubs replace
     players Miami took. The run stops, checkpointed and pushed, on the day a Miami trade executes;
  4. the day's Miami game (one at a time, so an injury reaches the next game) and league games are built, their
     inputs frozen (`game_requests.freeze`) and checked against the dated records;
  5. awards announced that morning are decided (an exact tie is an engine draw);
  6. the day's games are played through the engine's direct route and written back into the career record.
Before opening night a day is training camp and the preseason (`scripts/run_camp.py`, every stage due by the day,
its draws by the engine, its games played). After the regular season a day is: season awards announced that morning, the day's playoff games built
(`scripts/playoff_day.py`, Miami's one at a time) and played, then the bracket brought up to date; the market,
trade scan and staff reviews are closed. The day the summer market's record exists and the rollover is dated, the
next season becomes live (`scripts/rollover.py`), and its own calendar (`runtime/seasons.py`) routes every later day.

Every chance answer is an engine draw; nothing here chooses an outcome. Each day writes results back lightly (notes,
injuries, registry, team records). Every Sunday the full write-back, page rebuild and repository validation run;
every other Sunday and at the target date the full test suite runs too and the week is pushed. A push also happens
when the engine refuses a game because its deployed code or library differs.

Stops: a pending player decision or consultation for Wade (`current_state.pending_player_decisions`), any step
that fails, failed validation or tests, or a game the engine still refuses after a push.

Environment: ENGINE_API_TOKEN (never printed), and optionally ADVANCE_COMMIT_TRAILER appended to each commit.
"""
import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ADVANCE_LIGHT", "1")         # builders skip the report rebuild; the checkpoint does it
MIAMI_RESULTS = ("career/Dwyane_Wade/{season}/05_Preseason/Game_*.result.json",
                 "career/Dwyane_Wade/{season}/06_Regular_Season/*/*/Game_*.result.json",
                 "career/Dwyane_Wade/{season}/08_Playoffs/*/Game_*.result.json")


def live():
    """The live season (runtime/seasons.py): it changes when the rollover runs, so it is read every time."""
    from runtime.seasons import active
    return active(ROOT)


def season_dates():
    from runtime.seasons import dates
    return dates(live(), ROOT)


def miami_results():
    return [p for pattern in MIAMI_RESULTS for p in ROOT.glob(pattern.format(season=live()))]


class Stop(Exception):
    pass


def say(msg):
    print(msg, flush=True)


def run(*args, ok=(0,), show=True):
    p = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip()
    if show and out:
        say("\n".join("    " + line for line in out.splitlines()[-12:]))
    if p.returncode not in ok:
        raise Stop(f"{' '.join(args)} exited {p.returncode}")
    return out


def git(*args):
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def state_file():
    return ROOT / f"career/Dwyane_Wade/{live()}/current_state.json"


def state():
    return json.loads(state_file().read_text(encoding="utf-8"))


def write_state(data):
    state_file().write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def wade_waits():
    pending = state().get("pending_player_decisions") or []
    if pending:
        raise Stop("Wade has a decision to make: " + "; ".join(map(str, pending)))


def commit(message):
    git("add", "-A")
    code, _ = git("diff", "--cached", "--quiet")
    if code:
        trailer = os.getenv("ADVANCE_COMMIT_TRAILER", "")
        git("commit", "-q", "-m", message + (f"\n\n{trailer}" if trailer else ""))


def checkpoint(day, push=True):
    """The full write-back and page rebuild, validation; with `push`, the full suite and the push."""
    # Every derived record rebuilt from its sources, then validation (scripts/reconcile.py): a stale total or page is
    # fixed here, so only a real conflict between source records stops the run.
    if "passed" not in run("scripts/reconcile.py", ok=(0, 1)):
        raise Stop("validation failed after rebuilding every derived record (a source conflict; see above)")
    commit(f"Advance {day}: checkpoint")
    if not push:
        return
    for _ in range(40):                                                    # roadmap 18b: journal and the published engine hash
        audit = run("scripts/audit_journal.py", ok=(0, 1), show=False)
        if "no problems" in audit or not any(code in audit for code in ("502", "503", "timed out", "unreachable")):
            break
        time.sleep(30)                                                     # the engine is restarting (a deploy); wait
    if "no problems" not in audit:
        raise Stop("the engine journal audit failed: " + audit.splitlines()[-1][:200])
    tests = run("scripts/run_tests.py", ok=(0, 1), show=False)
    say("    " + tests.splitlines()[-1])
    if not tests.splitlines()[-1].endswith("OK"):
        raise Stop("test suite failed")
    for attempt in range(5):
        code, out = git("push", "-q", "origin", "HEAD:milestone-1")
        if code == 0:
            return
        if "rejected" in out or "fetch first" in out:
            # The results collector may have committed engine results meanwhile: keep ours, then validate the merge.
            git("fetch", "-q", "origin", "milestone-1")
            code, out = git("merge", "-q", "-X", "ours", "--no-edit", "origin/milestone-1")
            if code:
                regenerate_after_merge(out)
            else:                                 # generated views kept our copy (`merge=binary`): rebuild from merged records
                run("scripts/reconcile.py", ok=(0, 1), show=False)
                commit("Regenerate views after merging origin")
            if "passed" not in run("scripts/validate_repository.py", ok=(0, 1), show=False):
                raise Stop("validation failed after merging origin")
            continue
        time.sleep(2 ** (attempt + 1))
    raise Stop("push failed")


def regenerate_after_merge(out):
    """A merge left conflicts. Generated views (`merge=binary` in .gitattributes) keep our copy and are regenerated from
    the merged records; any other conflicted path is a real conflict and stops the run."""
    _, listing = git("diff", "--name-only", "--diff-filter=U")
    paths = [p for p in listing.splitlines() if p.strip()]
    _, attrs = git("check-attr", "merge", "--", *paths) if paths else (0, "")
    real = [line.split(":")[0] for line in attrs.splitlines() if not line.endswith(": binary")]
    if not paths or real:
        git("merge", "--abort")
        raise Stop("merge with origin failed: " + (", ".join(real[:5]) or out))
    git("checkout", "--ours", "--", *paths)
    run("scripts/reconcile.py", ok=(0, 1), show=False)
    git("add", "-A")
    code, out = git("commit", "-q", "--no-edit")
    if code:
        raise Stop("merge commit failed: " + out)
    say(f"    merged origin: {len(paths)} generated view(s) regenerated")


def draws_pending():
    return any(not p.with_name(p.name.replace(".decision.json", ".decision.result.json")).exists()
               for p in (ROOT / "career").rglob("*.decision.json"))


def draw():
    """Draw every pending decision packet; while the engine restarts (a deploy), wait and try again."""
    for _ in range(40):
        if not draws_pending():
            return
        out = run("scripts/draw_decisions.py", ok=(0, 1))
        if not draws_pending():
            return
        if not any(code in out for code in ("error 502", "error 503", "unreachable", "timed out")):
            raise Stop("a decision draw failed: " + out.splitlines()[-1][:200])
        time.sleep(30)
    raise Stop("decision draws still failing after waiting for the engine")


def play(day):
    """Every pending game through `day`; if the engine refuses (its code or library differs), push and wait."""
    pushed = False
    for _ in range(40):
        out = run("scripts/play_games.py", day, ok=(0, 1), show=False)
        refused = [l for l in out.splitlines() if l and not l.startswith(("played", "already_played")) and "written" not in l]
        if not refused:
            say("    " + out.splitlines()[-1])
            return
        if all(("refused 502" in l or "refused 503" in l or "unreachable" in l) for l in refused):
            time.sleep(30)                                   # the engine is restarting (a deploy); wait, do not push
            continue
        if not pushed:
            say(f"    the engine refused a game ({refused[0][:100]}); pushing so it redeploys")
            run("scripts/write_back_results.py", "--write", show=False)
            checkpoint(day)
            pushed = True
        time.sleep(30)
    raise Stop("games still refused after the push: " + refused[0][:200])


def summary(day):
    for path in sorted(miami_results()):
        r = json.loads(path.read_text(encoding="utf-8"))
        if r["game_date"] != day:
            continue
        side = "home" if r["home"] == "Miami Heat" else "away"
        other = "away" if side == "home" else "home"
        won = r["final_score"][side] > r["final_score"][other]
        say(f"    Miami {'W' if won else 'L'} {r['final_score'][side]}-{r['final_score'][other]} "
            f"{'vs' if side == 'home' else 'at'} {r[other]}" + (" (playoffs)" if r.get("game_type") == "playoff" else ""))
        for p in r["player_stats"][side]:
            if p["player_id"] == "Dwyane Wade":
                say(f"    Wade {p['minutes']:.1f} min, {p['pts']} pts, {p['orb'] + p['drb']} reb, {p['ast']} ast, "
                    f"FG {p['fgm']}-{p['fga']}, 3P {p['tpm']}-{p['tpa']}, FT {p['ftm']}-{p['fta']}")
        # Wade's injuries and absences, drawn by the engine, are always reported (the user's request, December 2004).
        for e in (r.get("injuries") or []) + (r.get("absences") or []):
            if e.get("player_id") == "Dwyane Wade":
                line = (f"WADE {'INJURY' if e in (r.get('injuries') or []) else 'ABSENCE'}: {e.get('kind', 'unspecified')}, "
                        f"{e.get('games_out', '?')} game(s) out (engine draw, {r['event_id']})")
                say("    " + line)
                WADE_NEWS.append(f"{day}  {line}")
                if isinstance(e.get("games_out"), int) and e["games_out"] >= LONG_INJURY_GAMES:
                    WADE_LONG.append(f"{day}  {line}")


def seed_playoffs(day):
    """The first day after the regular season: set the playoff bracket once every regular-season game is closed, drawing any
    tie the procedure cannot break (`scripts/seed_playoffs.py`). Nothing to do once the bracket exists."""
    from runtime import playoffs
    if playoffs.read(ROOT) is not None:
        return
    for _ in range(5):
        out = run("scripts/seed_playoffs.py", "--write", ok=(0, 1), show=False)
        if playoffs.read(ROOT) is not None:
            say("    playoffs seeded")
            return
        if "tiebreak drawing needed" in out and draws_pending():
            draw()
            continue
        raise Stop("the playoffs cannot be seeded: " + out.splitlines()[-1][:200])
    raise Stop("the playoffs cannot be seeded after the tiebreak drawings")


def playoff_day(day):
    """After the regular season: awards, the day's playoff games, then the bracket. The market, trade scan and staff
    reviews are closed (the rotation in force carries into the playoffs)."""
    data = state()
    data["current_area"] = "08_Playoffs"
    write_state(data)
    option_day(day)                                     # veteran options at the end of June, before the summer market
    run("scripts/decide_awards.py", "--write", ok=(0, 1))
    draw()
    run("scripts/decide_awards.py", "--write", show=False)
    seed_playoffs(day)
    run("scripts/playoff_day.py", "--refresh", show=False)
    for _ in range(150):                                                # lottery draws and draft picks, one at a time
        run("scripts/offseason_day.py", "--write", day, show=False)
        if not draws_pending():
            break
        draw()
    say("    " + run("scripts/offseason_day.py", "--write", day, show=False).splitlines()[0])
    run("scripts/playoff_day.py", "--build", day, show=False)
    national_day(day)                                    # FIBA tournaments in the summer (runtime/national.py)
    problems = run("-c", "from runtime.game_requests import frozen_errors; print('\\n'.join(frozen_errors()))", show=False)
    if problems:
        raise Stop("frozen inputs differ from the records: " + "; ".join(problems.splitlines()[:3]))
    wade_waits()
    play(day)


def rollover_day(day):
    """The day the summer market's record exists and the rollover is dated: the next season becomes live."""
    from runtime.rollover import Rollover
    if Rollover(ROOT).blockers(day):
        return False
    say("    " + run("scripts/rollover.py", "--write", show=False).splitlines()[-1][:200])
    return True


def camp_day(day):
    """Training camp and preseason (scripts/run_camp.py, every stage due by the day), then the day's preseason games."""
    data = state()
    data["current_area"] = data.get("current_area") if data.get("current_area") in ("04_Training_Camp", "05_Preseason") else "04_Training_Camp"
    write_state(data)
    option_day(day)
    miami_trade_day(day)                                    # Wade's trade requests answered; no scan before opening night
    out = run("scripts/run_camp.py", "--write", day, show=False)
    if draws_pending():
        draw()
        out = run("scripts/run_camp.py", "--write", day, show=False)
    say("    " + out.splitlines()[0][:200])
    national_day(day)                                    # a tournament running into training camp
    problems = run("-c", "from runtime.game_requests import frozen_errors; print('\\n'.join(frozen_errors()))", show=False)
    if problems:
        raise Stop("frozen inputs differ from the records: " + "; ".join(problems.splitlines()[:3]))
    wade_waits()
    play(day)


TRADES_TODAY = []
WADE_NEWS = []                                   # Wade injuries and absences this run, repeated at the end
WADE_LONG = []                                   # a long Wade injury stops the run like a Miami trade
LONG_INJURY_GAMES = 10


def national_day(day):
    """National-team tournaments (scripts/national_day.py): selection, roster lock, ties, the day's game requests.
    Each invitation answer is one engine draw, so the step repeats until nothing is pending."""
    for _ in range(60):
        out = run("scripts/national_day.py", "--write", day, show=False)
        for line in out.splitlines():
            if line and not line.startswith("national:"):
                say("    " + line)
                if line.startswith("WADE"):
                    WADE_NEWS.append(f"{day}  {line}")
        if not draws_pending():
            return
        draw()
    raise Stop("national-team draws still pending after 60 rounds")


def national_after(day):
    for line in run("scripts/national_day.py", "--after", day, show=False).splitlines():
        if line:
            say("    " + line)
            if "Wade" in line or line.startswith("USA"):
                WADE_NEWS.append(f"{day}  {line}")


def option_day(day):
    """Contract options for every club due by the day (scripts/option_day.py): close calls drawn by the engine."""
    out = run("scripts/option_day.py", "--write", day, show=False)
    if draws_pending():
        draw()
        out = run("scripts/option_day.py", "--write", day, show=False)
    if not out.splitlines()[-1].startswith("options: 0 decided"):
        say("    " + out.splitlines()[-1])


def miami_trade_day(day):
    """Miami's in-season trades (scripts/run_trade.py --season-day): drawn answers applied, a due scan's proposal
    written and drawn by the engine, an accepted trade executed the same day. Every line is reported."""
    out = run("scripts/run_trade.py", "--season-day", day, show=False)
    if draws_pending():
        draw()
        out += "\n" + run("scripts/run_trade.py", "--season-day", day, show=False)
    for line in out.splitlines():
        if line.startswith(("MIAMI TRADE", "Miami trade", "Miami proposes", "Wade's request", "trade offers")):
            say("    " + line)
        if line.startswith("MIAMI TRADE"):
            TRADES_TODAY.append(line)


def advance_day(day):
    from runtime import roster_moves
    say(f"== {day}")
    wade_waits()
    data = state()
    data["current_date"] = max(day, data["current_date"])
    write_state(data)
    gates = season_dates()
    if day > gates["regular_season_end"]:
        if rollover_day(day):                                # the summer is over: the next season is live from today
            return close_day(day)
        playoff_day(day)
        return close_day(day, playoffs=True)
    if day < gates["opening_night"]:
        if day >= (gates["training_camp_opens"] or day):
            camp_day(day)
        return close_day(day)
    moves = roster_moves.ctx(ROOT, day)
    if day in (moves.waive_by, moves.guarantee):
        run("scripts/guarantee_review.py", "--write", day)
    if run("scripts/review_rotation.py", "--check", day, ok=(0, 1), show=False).startswith("staff review due"):
        run("scripts/review_rotation.py", "--write", day, ok=(0, 1))
        draw()
        run("scripts/review_rotation.py", "--write", day)
    run("scripts/league_day.py", "--write", day)
    if draws_pending():
        draw()
        run("scripts/league_day.py", "--write", day)
    option_day(day)
    miami_trade_day(day)
    run("scripts/club_replacements.py", "--write", ok=(0, 1), show=False)
    run("scripts/build_season_games.py", "--write", day)
    run("scripts/build_league_slate.py", "--write", day, show=False)
    national_day(day)                                    # a qualifying window in the season (none before 2017)
    problems = run("-c", "from runtime.game_requests import frozen_errors; print('\\n'.join(frozen_errors()))", show=False)
    if problems:
        raise Stop("frozen inputs differ from the records: " + "; ".join(problems.splitlines()[:3]))
    run("scripts/decide_awards.py", "--write", ok=(0, 1))
    draw()
    run("scripts/decide_awards.py", "--write", show=False)
    wade_waits()
    play(day)
    close_day(day)


def close_day(day, playoffs=False):
    results = sorted(miami_results(), key=lambda p: json.loads(p.read_text(encoding="utf-8"))["game_date"])
    if results:
        data = state()
        data["last_closed_event"] = json.loads(results[-1].read_text(encoding="utf-8"))["event_id"]
        write_state(data)
    run("scripts/write_back_results.py", "--write", "--light", show=False)
    national_after(day)                                  # national results: Wade's notes, bracket, tournament close
    # Name each new Miami injury or absence (runtime/injury_types.py): one engine draw each, then record it.
    run("scripts/injury_types.py", "--write", show=False)
    if draws_pending():
        draw()
    for line in run("scripts/injury_types.py", "--write", show=False).splitlines():
        if not line.startswith("injury types:"):
            say("    " + line)
            if "Dwyane Wade" in line:
                WADE_NEWS.append(f"{day}  {line.strip()}")
    if playoffs:
        say("    " + run("scripts/playoff_day.py", "--refresh", show=False).splitlines()[-1])
        run("scripts/decide_awards.py", "--write", ok=(0, 1))        # the Finals MVP is named on the clinching night
        draw()
        run("scripts/decide_awards.py", "--write", show=False)
        run("scripts/playoff_day.py", "--close")
    summary(day)
    commit(f"Advance {day}")
    wade_waits()


def miami_series_decided(day):
    """The Miami series decided on `day`, as text, or None."""
    from runtime import playoffs
    record = playoffs.read(ROOT)
    for s in (record or {}).get("series", []):
        if "Miami Heat" in s["clubs"] and s.get("winner") and s.get("clinched_on") == day:
            other = next(c for c in s["clubs"] if c != "Miami Heat")
            return (f"{s.get('round', s['id'])}: {s['winner']} won the series "
                    f"{max(s['wins'].values())}-{min(s['wins'].values())} (Miami vs {other})")
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--to", required=True, help="the last day to play")
    parser.add_argument("--from", dest="start", help="first day (default: the career clock's day, rerun safely)")
    parser.add_argument("--series-end", action="store_true",
                        help="also stop (with the checkpoint and push) on the day a Miami playoff series is decided")
    parser.add_argument("--through-injuries", action="store_true",
                        help=f"keep going after a Wade injury of {LONG_INJURY_GAMES}+ games (by default the run stops, checkpointed and pushed)")
    parser.add_argument("--through-trades", action="store_true",
                        help="keep going after a Miami trade (by default the run stops, checkpointed and pushed, the day one executes)")
    args = parser.parse_args()
    day = date.fromisoformat(args.start or state()["current_date"])
    end = date.fromisoformat(args.to)
    try:
        while day <= end:
            advance_day(day.isoformat())
            if TRADES_TODAY and not args.through_trades:
                checkpoint(day.isoformat())
                say("DONE: " + "; ".join(TRADES_TODAY))     # the user is told of every Miami trade the day it happens
                return 0
            if WADE_LONG and not args.through_injuries:
                checkpoint(day.isoformat())
                say("DONE: " + "; ".join(WADE_LONG))       # the user is told of a long Wade injury the day it happens
                return 0
            if args.series_end and miami_series_decided(day.isoformat()):
                checkpoint(day.isoformat())
                say(f"DONE: {miami_series_decided(day.isoformat())}")
                return 0
            if day == end or (day.weekday() == 6 and day.isocalendar()[1] % 2 == 0):
                checkpoint(day.isoformat())                  # every other Sunday: pages, validation, suite, push
            elif day.weekday() == 6:
                checkpoint(day.isoformat(), push=False)      # the Sundays between: pages and validation
            day += timedelta(days=1)
    except Stop as stop:
        say(f"STOPPED on {state()['current_date']}: {stop}")
        return 1
    if WADE_NEWS:
        say("Wade injuries and absences this run: " + "; ".join(WADE_NEWS))
    say(f"DONE through {end.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
