"""Stdlib-only line coverage (uses `trace`) so the project runs with just pytest.

If you have `pytest-cov` installed you can instead run:
    pytest --cov=bank --cov-branch --cov-report=term-missing --cov-report=html
"""
import json
import os
import sys
import time
import trace

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "bank", "account.py")
os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)

tracer = trace.Trace(count=True, trace=False)
start = time.perf_counter()
rc = tracer.runfunc(pytest.main, ["-q", "-p", "no:cacheprovider"])
elapsed = time.perf_counter() - start

counts = tracer.results().counts
executed = {ln for (fn, ln), c in counts.items() if os.path.abspath(fn) == TARGET}
executable = set(trace._find_executable_linenos(TARGET))
executable.discard(0)
executable.discard(None)
missed = sorted(executable - executed)
cov = 100.0 * len(executable & executed) / len(executable)

report = {
    "file": "bank/account.py",
    "executable_lines": len(executable),
    "covered_lines": len(executable & executed),
    "missed_lines": missed,
    "line_coverage_pct": round(cov, 1),
    "pytest_exit_code": int(rc),
}
with open(os.path.join(ROOT, "reports", "coverage.json"), "w") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
sys.exit(int(rc))
