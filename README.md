# Banking Module – pytest Unit Testing

Tool: **pytest 9** (fixtures, parametrization, mocks via `unittest.mock`, JUnit XML report)
SUT: `bank/account.py` – Python banking transactions (deposit, withdraw, transfer, tiered interest, freeze, daily limit).

## Run
```bash
pip install pytest            # only requirement
python -m pytest              # runs 57 tests, writes reports/junit.xml
python run_coverage.py        # line coverage (stdlib trace) -> reports/coverage.json
python mutation_check.py      # seeds 10 defects into a copy, checks tests catch them
```
Optional (if pytest-cov is installed): `pytest --cov=bank --cov-branch --cov-report=html`

## Layout
```
bank/account.py        System under test
tests/conftest.py      Shared fixtures
tests/test_account.py  44 test cases (TC-01..TC-44) -> 57 executions via parametrize
run_coverage.py        Stdlib line coverage
mutation_check.py      Seeded-defect (mutation) check
reports/               Logs, JUnit XML, coverage + mutation results
```

## Results (last run)
- 57 passed, 0 failed, 0 skipped, ~0.08 s
- Line coverage of `bank/account.py`: 100 % (100/100 lines). Branch coverage not measured.
- Mutation check: 10/10 seeded defects detected
