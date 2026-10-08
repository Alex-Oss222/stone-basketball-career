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
that fails, failed validation or tests, or a game the engine still refuses after a push. A failing step prints the
last FAIL_TAIL lines of its own output (a step judged by its output too: the games, draws, frozen inputs, validation,
the journal audit, the suite, the push), and an exception raised inside the driver its whole traceback, before the
stop. A games step that did not finish (a traceback, not an engine refusal) stops at once, with no push and no wait.

Miami news: an in-season trade (`scripts/run_trade.py --season-day`) and a trade in the summer market or on draft night
(`scripts/offseason_day.py`, read from the market's dated events and the draft record) both print a line starting
"MIAMI TRADE" and stop the run the day they happen, checkpointed and pushed (`--through-trades` reports them and goes
on); the summer's Miami picks, signings, offer sheets and losses are reported the same day. A stop on news records
its lines in `current_state` (`reported_stop`), so resuming on that day reports them again without stopping a second
time.

Environment: ENGINE_API_TOKEN (never printed), and optionally ADVANCE_COMMIT_TRAILER appended to each commit.
"""
import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

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


FAIL_TAIL = 40                                   # lines of a failing step's own output printed before the stop


def say(msg):
    print(msg, flush=True)


def tail(text, lines=FAIL_TAIL):
    """The last `lines` lines of a step's output, indented like the driver's other output."""
    return "\n".join("    " + line for line in text.splitlines()[-lines:])


def run(*args, ok=(0,), show=True):
    """Run a step. Its combined output's last 12 lines are shown with `show`; a step that exits outside `ok` always
    prints its last FAIL_TAIL lines (shown or not), so the error that stopped it is on screen, then stops the run."""
    p = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip()
    if p.returncode not in ok:
        if out:
            say(tail(out))
        raise Stop(f"{' '.join(args)} exited {p.returncode}")
    if show and out:
        say(tail(out, 12))
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
    # A step judged by its output rather than its exit code prints its tail (FAIL_TAIL lines) before the stop too.
    rebuilt = run("scripts/reconcile.py", ok=(0, 1), show=False)
    if "passed" not in rebuilt:
        say(tail(rebuilt))
        raise Stop("validation failed after rebuilding every derived record (a source conflict; see above)")
    if rebuilt:
        say(tail(rebuilt, 12))
    commit(f"Advance {day}: checkpoint")
    if not push:
        return
    for _ in range(40):                                                    # roadmap 18b: journal and the published engine hash
        audit = run("scripts/audit_journal.py", ok=(0, 1), show=False)
        if "no problems" in audit or not any(code in audit for code in ("502", "503", "timed out", "unreachable")):
            break
        time.sleep(30)                                                     # the engine is restarting (a deploy); wait
    if "no problems" not in audit:
        say(tail(audit))
        raise Stop("the engine journal audit failed: " + (audit.splitlines() or [""])[-1][:200])
    tests = run("scripts/run_tests.py", ok=(0, 1), show=False)
    last = (tests.splitlines() or [""])[-1]
    if not last.endswith("OK"):
        say(tail(tests))
        raise Stop("test suite failed")
    say("    " + last)
    for attempt in range(5):
        code, push_out = git("push", "-q", "origin", "HEAD:milestone-1")    # kept apart from the merge's output below
        if code == 0:
            return
        if "rejected" in push_out or "fetch first" in push_out:
            # The results collector may have committed engine results meanwhile: keep ours, then validate the merge.
            git("fetch", "-q", "origin", "milestone-1")
            code, out = git("merge", "-q", "-X", "ours", "--no-edit", "origin/milestone-1")
            if code:
                regenerate_after_merge(out)
            else:                                 # generated views kept our copy (`merge=binary`): rebuild from merged records
                run("scripts/reconcile.py", ok=(0, 1), show=False)
                commit("Regenerate views after merging origin")
            validation = run("scripts/validate_repository.py", ok=(0, 1), show=False)
            if "passed" not in validation:
                say(tail(validation))
                raise Stop("validation failed after merging origin")
            continue
        time.sleep(2 ** (attempt + 1))
    say(tail(push_out))                                  # the last push's own refusal, never a quiet merge's empty output
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
    """Draw every pending decision packet; while the engine restarts (a deploy), wait and try again. Each round shows its
    last 12 lines; a failed draw, judged by the packets still pending, prints its tail (FAIL_TAIL lines) before the stop."""
    for _ in range(40):
        if not draws_pending():
            return
        out = run("scripts/draw_decisions.py", ok=(0, 1), show=False)
        if not draws_pending():
            if out:
                say(tail(out, 12))
            return
        if not any(code in out for code in ("error 502", "error 503", "unreachable", "timed out")):
            say(tail(out))
            raise Stop("a decision draw failed: " + (out.splitlines() or ["no output"])[-1][:200])
        if out:
            say(tail(out, 12))
        time.sleep(30)
    say(tail(out))
    raise Stop("decision draws still failing after waiting for the engine")


PLAYED = re.compile(r"^\d+ of \d+ game\(s\) written$", re.M)   # scripts/play_games.py's closing line


def play(day):
    """Every pending game through `day`; if the engine refuses (its code or library differs), push and wait.
    `scripts/play_games.py` exits 1 both when the engine refuses a game and when the script itself fails, so the two are
    told apart by its closing "N of M game(s) written" line (PLAYED): a run without it did not finish (a traceback, a
    missing token), is no engine refusal, and stops at once with its output's tail (FAIL_TAIL lines), no push and no wait.
    A finished run's refusals are its status lines, the output before the closing line (stderr follows it)."""
    pushed = False
    for _ in range(40):
        out = run("scripts/play_games.py", day, ok=(0, 1), show=False)
        closing = PLAYED.search(out)
        if not closing:
            say(tail(out))
            raise Stop(f"scripts/play_games.py {day} did not finish: " + (out.splitlines() or ["no output"])[-1][:200])
        refused = [l for l in out[:closing.start()].splitlines() if l and not l.startswith(("played", "already_played"))]
        if not refused:
            say("    " + closing.group(0))
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
    say(tail(out))
    raise Stop("games still refused after the push: " + refused[0][:200])


def frozen_check():
    """The frozen engine inputs of every built request recomputed from the committed records
    (`runtime.game_requests.frozen_errors`); a step judged by its output, so any difference prints its tail (FAIL_TAIL
    lines) before the stop, which names the first three."""
    problems = run("-c", "from runtime.game_requests import frozen_errors; print('\\n'.join(frozen_errors()))", show=False)
    if problems:
        say(tail(problems))
        raise Stop("frozen inputs differ from the records: " + "; ".join(problems.splitlines()[:3]))


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
        say(tail(out))
        raise Stop("the playoffs cannot be seeded: " + (out.splitlines() or [""])[-1][:200])
    raise Stop("the playoffs cannot be seeded after the tiebreak drawings")


def playoff_day(day):
    """After the regular season: awards, the day's playoff games, then the bracket. The market, trade scan and staff
    reviews are closed (the rotation in force carries into the playoffs)."""
    data = state()
    data["current_area"] = "08_Playoffs"
    write_state(data)
    extension_day(day)                                  # veteran extensions on June 29 (runtime/extensions.py)
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
    out = run("scripts/offseason_day.py", "--write", day, show=False)
    say("    " + next((line for line in out.splitlines() if not line.startswith(MARKET_NEWS)), ""))
    market_news(out)
    run("scripts/playoff_day.py", "--build", day, show=False)
    national_day(day)                                    # FIBA tournaments in the summer (runtime/national.py)
    frozen_check()
    wade_waits()
    play(day)


def rollover_day(day):
    """The day the summer market's record exists and the rollover is dated: the next season becomes live."""
    from runtime.extensions import ExtensionError
    from runtime.rollover import Rollover
    try:
        if Rollover(ROOT).blockers(day):
            return False
    except ExtensionError as e:                          # a missed or unresolved extension day blocks the rollover
        raise Stop(str(e))
    say("    " + run("scripts/rollover.py", "--write", show=False).splitlines()[-1][:200])
    return True


def camp_day(day):
    """Training camp and preseason (scripts/run_camp.py, every stage due by the day), then the day's preseason games."""
    data = state()
    data["current_area"] = data.get("current_area") if data.get("current_area") in ("04_Training_Camp", "05_Preseason") else "04_Training_Camp"
    write_state(data)
    extension_day(day)                                      # the October 31 extension deadline falls in the preseason
    option_day(day)
    miami_trade_day(day)                                    # Wade's trade requests answered; no scan before opening night
    out = run("scripts/run_camp.py", "--write", day, show=False)
    if draws_pending():
        draw()
        out = run("scripts/run_camp.py", "--write", day, show=False)
    say("    " + out.splitlines()[0][:200])
    national_day(day)                                    # a tournament running into training camp
    frozen_check()
    wade_waits()
    play(day)


TRADES_TODAY = []                                # the day's Miami trades, in season or in the summer market
WADE_NEWS = []                                   # Wade injuries and absences this run, repeated at the end
WADE_LONG = []                                   # a long Wade injury stops the run like a Miami trade
LONG_INJURY_GAMES = 10
MARKET_NEWS = ("MIAMI TRADE", "MIAMI SIGNING", "MIAMI OFFER SHEET", "MIAMI LOSES", "MIAMI DRAFT")   # scripts/offseason_day.py


def market_news(out):
    """The summer's Miami lines of the day (`scripts/offseason_day.py`, read from the market's dated events and, on draft
    night, the draft record): each is reported; a trade starts "MIAMI TRADE" in the in-season format and stops the run
    like one."""
    for line in out.splitlines():
        if line.startswith(MARKET_NEWS):
            say("    " + line)
            if line.startswith("MIAMI TRADE") and line not in TRADES_TODAY:
                TRADES_TODAY.append(line)


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


def extension_day(day):
    """Contract extensions on their own date (scripts/extension_day.py, runtime/extensions.py): every club's decision
    packets drawn by the engine, then applied; Wade's offer stops the run through wade_waits(). A refused day (missed,
    ahead of the clock, or behind an unresolved decision) exits 1, so run() prints its reason and stops."""
    out = run("scripts/extension_day.py", "--write", day, show=False)
    for _ in range(3):
        if not draws_pending():
            break
        draw()
        out = run("scripts/extension_day.py", "--write", day, show=False)
    for line in out.splitlines():
        if line.startswith(("EXTENSION", "MIAMI EXTENSION", "WADE EXTENSION")):
            say("    " + line)
            if line.startswith("WADE"):
                WADE_NEWS.append(f"{day}  {line}")
    last = (out.splitlines() or [""])[-1]
    if last and not last.startswith("extensions: 0 decided, 0 draw packet(s) written, 0 applied"):
        say("    " + last)


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
    extension_day(day)                                   # an October 31 deadline after opening night
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
    frozen_check()
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


def reported(day):
    """Lines a stop on `day` already reported (`current_state.reported_stop`): a resumed day reports them again but does
    not stop on them a second time."""
    record = state().get("reported_stop") or {}
    return set(record.get("lines") or []) if record.get("date") == day else set()


def stop_on_news(day, lines):
    """Stop the run on the day's news (a Miami trade, a long Wade injury): record the lines (`reported_stop`), then the
    checkpoint and push, then tell the user."""
    data = state()
    record = data.get("reported_stop") or {}
    kept = list(record.get("lines") or []) if record.get("date") == day else []
    data["reported_stop"] = {"date": day, "lines": kept + [line for line in lines if line not in kept]}
    write_state(data)
    checkpoint(day)
    say("DONE: " + "; ".join(lines))


def news_before_stop():
    """A stop for another reason (a failing step, Wade's pending decision) repeats the day's Miami news first, so a trade
    reported earlier in the day is not lost above the failure."""
    news = TRADES_TODAY + WADE_LONG
    if news:
        say("Miami news of the day before the stop: " + "; ".join(news))


def clock_or(default):
    """The career clock's day for a stop message, or `default` when the state cannot be read."""
    try:
        return state()["current_date"]
    except Exception:                                   # the state itself is unreadable: name the run's own day
        return default


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
            TRADES_TODAY.clear()
            WADE_LONG.clear()
            advance_day(day.isoformat())
            done = reported(day.isoformat())
            trades = [line for line in TRADES_TODAY if line not in done]
            if trades and not args.through_trades:
                stop_on_news(day.isoformat(), trades)       # the user is told of every Miami trade the day it happens
                return 0
            injuries = [line for line in WADE_LONG if line not in done]
            if injuries and not args.through_injuries:
                stop_on_news(day.isoformat(), injuries)     # the user is told of a long Wade injury the day it happens
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
        news_before_stop()
        say(f"STOPPED on {clock_or(day.isoformat())}: {stop}")
        return 1
    except Exception as exc:                               # a step raised inside the driver: its traceback, then the stop
        # The whole traceback, chained causes included (their root is at the top), as Python itself would print it.
        say("\n".join("    " + line for line in traceback.format_exc().rstrip().splitlines()))
        news_before_stop()
        say(f"STOPPED on {clock_or(day.isoformat())}: {type(exc).__name__}: {exc}")
        return 1
    if WADE_NEWS:
        say("Wade injuries and absences this run: " + "; ".join(WADE_NEWS))
    say(f"DONE through {end.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
