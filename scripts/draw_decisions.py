#!/usr/bin/env python3
"""Draw every pending decision request on the running engine now, without waiting for a redeploy.

For each committed or newly written `*.decision.json` with no `*.decision.result.json` beside it, the
request is sent unchanged to the engine's authenticated `POST /decisions` route. The engine journals
and draws it exactly as it would at boot, keeps the first draw for ever and refuses a changed packet
under the same event id. The answer is checked against the request (`collect_results.result_errors`)
and written as the same result file the collector writes. The request files must still be committed:
the next deploy's boot scan re-verifies each one against the stored draw.

Games are not drawn here: a game request needs the repository's dated inputs on the engine, so games
are still played by pushing to the branch Railway tracks.

  ENGINE_URL         base URL of the engine (default: the Railway domain)
  ENGINE_API_TOKEN   bearer token for the authenticated routes; read from the environment, never printed
"""
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.decisions import find_decisions, load_decision   # noqa: E402
from scripts.collect_results import URL, result_errors, write_result   # noqa: E402


def post(data, token, url=URL, opener=urlopen):
    body = json.dumps(data).encode("utf-8")
    request = Request(f"{url}/decisions", data=body, method="POST",
                      headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    with opener(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def draw_pending(root=ROOT, token=None, send=None):
    """Returns [(event_id, status or error)] for every pending decision under career/."""
    token = token or os.getenv("ENGINE_API_TOKEN")
    if not token and send is None:
        raise SystemExit("ENGINE_API_TOKEN is not set")
    send = send or (lambda data: post(data, token))
    report = []
    for path in find_decisions(root):
        out = path.with_name(path.name.replace(".decision.json", ".decision.result.json"))
        if out.exists():
            continue
        data = load_decision(path)
        try:
            served = send(data)
        except HTTPError as exc:
            report.append((data["event_id"], f"error {exc.code}: {exc.read().decode('utf-8', 'replace')[:200]}"))
            continue
        except (URLError, TimeoutError) as exc:
            report.append((data["event_id"], f"unreachable: {exc}"))
            continue
        status = served.pop("status", None)
        problems = result_errors(data, served, "decision")
        if problems:
            report.append((data["event_id"], "refused: " + "; ".join(problems)))
            continue
        write_result(out, served)
        report.append((data["event_id"], f"{status}: {served['outcome']}"))
    return report


def main():
    report = draw_pending()
    for event_id, status in report:
        print(f"{event_id:<48} {status}")
    print(f"{len(report)} decision(s) sent")
    return 1 if any(s.startswith(("error", "refused", "unreachable")) for _, s in report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
