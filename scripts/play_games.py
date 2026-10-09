#!/usr/bin/env python3
"""Play every pending game request on the running engine now, without waiting for a redeploy.

For each committed or newly written `*.request.json` with no result beside it (Miami's game notes and
the league slate), in date order: the request and its input fingerprint
(`runtime.game_requests.input_fingerprint`) go to the engine's authenticated `POST /games` route. The
engine refuses the game unless its deployed copy gives the same fingerprint, so a game played this way
replays identically at the next boot; then it journals and plays it exactly as the boot scan would and
keeps the first result for ever. The answer is checked against the request
(`collect_results.result_errors`) and written as the same result file the collector writes. Requests
and results must still be committed. A refused game waits for the normal push and redeploy.

  ENGINE_URL         base URL of the engine (default: the Railway domain)
  ENGINE_API_TOKEN   bearer token for the authenticated routes; read from the environment, never printed
"""
import json
import os
from pathlib import Path
import sys
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.game_requests import find_requests, input_fingerprint   # noqa: E402
from scripts.collect_results import URL, result_errors, write_result   # noqa: E402


def result_path(request):
    return request.with_name(request.name.replace(".request.json", ".result.json"))


def pending(root=ROOT):
    rows = []
    for path in find_requests(root):
        if not result_path(path).exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            rows.append((data["game_date"], str(path), path, data))
    return [(p, d) for _, _, p, d in sorted(rows)]


def post(body, token, url=URL, opener=urlopen):
    request = Request(f"{url}/games", data=json.dumps(body).encode("utf-8"), method="POST",
                      headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    with opener(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def play_pending(root=ROOT, token=None, send=None, until=None):
    """Returns [(event_id, status or error)] for every pending game on or before `until`."""
    token = token or os.getenv("ENGINE_API_TOKEN")
    if not token and send is None:
        raise SystemExit("ENGINE_API_TOKEN is not set")
    send = send or (lambda body: post(body, token))
    report = []
    for path, data in pending(root):
        if until and data["game_date"] > until:
            continue
        body = {"path": path.relative_to(root).as_posix(), "request": data, "fingerprint": input_fingerprint(path, root)}
        try:
            served = send(body)
        except HTTPError as exc:
            report.append((data["event_id"], f"refused {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}"))
            continue
        except (URLError, TimeoutError, ConnectionError, HTTPException) as exc:   # a dropped or cut-off connection is transient
            report.append((data["event_id"], f"unreachable: {exc}"))
            continue
        status = served.pop("status", None)
        problems = result_errors(data, served, "game")
        if problems:
            report.append((data["event_id"], "result refused: " + "; ".join(problems)))
            continue
        write_result(result_path(path), served)
        report.append((data["event_id"], status))
    return report


def main():
    until = sys.argv[1] if len(sys.argv) > 1 else None
    report = play_pending(until=until)
    for event_id, status in report:
        print(f"{status:<14} {event_id}")
    print(f"{sum(1 for _, s in report if s in ('played', 'already_played'))} of {len(report)} game(s) written")
    return 0 if all(s in ("played", "already_played") for _, s in report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
