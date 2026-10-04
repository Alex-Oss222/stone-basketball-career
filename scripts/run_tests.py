#!/usr/bin/env python3
"""Run the whole test suite, one test module per process, several at a time.

    python scripts/run_tests.py            all modules, as many at once as there are CPUs (at least 2)
    python scripts/run_tests.py -j 4       four at a time

Every module under tests/ runs in full; the exit status is nonzero when any module fails, and its output is
printed. The same suite as `python -m unittest discover -s tests`, only faster on several cores.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(module):
    p = subprocess.run([sys.executable, "-m", "unittest", f"tests.{module}"], cwd=ROOT, capture_output=True, text=True)
    out = p.stdout + p.stderr
    ran = re.search(r"^Ran (\d+) tests?", out, re.M)
    return module, p.returncode, int(ran.group(1)) if ran else 0, out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("-j", type=int, default=max(2, os.cpu_count() or 2))
    jobs = parser.parse_args().j
    modules = sorted(p.stem for p in (ROOT / "tests").glob("test_*.py"))
    failed, total = [], 0
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for module, code, ran, out in pool.map(run, modules):
            total += ran
            if code:
                failed.append(module)
                print(f"===== FAILED: {module}\n{out}", flush=True)
    print(f"{len(modules)} modules, {total} tests, {jobs} at a time: " + ("OK" if not failed else "FAILED " + ", ".join(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
