"""Tiny hand-rolled mutation check: seed known defects into a COPY of the SUT
and confirm the test-suite catches each one ("killed") or not ("survived").
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "bank", "account.py")

MUTANTS = [
    ("M1", "Deposit max boundary off-by-one", "value > MAX_DEPOSIT", "value >= MAX_DEPOSIT"),
    ("M2", "Deposit min boundary off-by-one", "value < MIN_DEPOSIT", "value <= MIN_DEPOSIT"),
    ("M3", "Daily limit uses >= instead of >", "self.withdrawn_today + value > DAILY_WITHDRAW_LIMIT", "self.withdrawn_today + value >= DAILY_WITHDRAW_LIMIT"),
    ("M4", "Min savings balance check off-by-one", "self.balance - value < MIN_SAVINGS_BALANCE", "self.balance - value <= MIN_SAVINGS_BALANCE"),
    ("M5", "Overdraft limit check off-by-one", "self.balance - value < -OVERDRAFT_LIMIT", "self.balance - value <= -OVERDRAFT_LIMIT"),
    ("M6", "Transfer rollback removed", "            self.balance += value\n            self.withdrawn_today -= value\n            raise", "            raise"),
    ("M7", "Tier-1 ceiling boundary wrong", "self.balance < TIER1_CEILING", "self.balance <= TIER1_CEILING"),
    ("M8", "Interest divided by 10 not 12", "self.monthly_interest_rate() / 12", "self.monthly_interest_rate() / 10"),
    ("M9", "Frozen check skipped on deposit", "    def deposit(self, amount):\n        self._check_active()\n", "    def deposit(self, amount):\n"),
    ("M10", "Self-transfer guard removed", "if target is self:", "if False:"),
]

results = []
for mid, desc, old, new in MUTANTS:
    with open(SRC) as f:
        code = f.read()
    assert old in code, f"pattern for {mid} not found"
    tmp = tempfile.mkdtemp()
    shutil.copytree(os.path.join(ROOT, "bank"), os.path.join(tmp, "bank"))
    shutil.copytree(os.path.join(ROOT, "tests"), os.path.join(tmp, "tests"))
    with open(os.path.join(tmp, "bank", "account.py"), "w") as f:
        f.write(code.replace(old, new, 1))
    p = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "-c", "/dev/null", "--rootdir", tmp, "tests"],
        cwd=tmp, capture_output=True, text=True,
    )
    killed = p.returncode != 0
    first_fail = next((l for l in p.stdout.splitlines() if l.startswith("FAILED")), "")
    results.append({"id": mid, "defect": desc, "killed": killed, "caught_by": first_fail.replace("FAILED ", "")[:90]})
    shutil.rmtree(tmp)

os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
with open(os.path.join(ROOT, "reports", "mutation.json"), "w") as f:
    json.dump(results, f, indent=2)
k = sum(r["killed"] for r in results)
for r in results:
    print(("KILLED  " if r["killed"] else "SURVIVED"), r["id"], r["defect"], "|", r["caught_by"])
print(f"\nMutation score: {k}/{len(results)} = {100*k/len(results):.0f}%")
