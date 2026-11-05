# functional-testing-2405207

[![CI](https://github.com/Miskat-SE/functional-testing-2405207/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Miskat-SE/functional-testing-2405207/actions/workflows/ci.yml)

Functional testing, CI/CD and live deployment for `target.py` (16 functions: 11 data-type, 5 mathematics).

| | |
|---|---|
| **Live site** | https://functional-testing-2405207.onrender.com |
| **Health / deployed commit** | https://functional-testing-2405207.onrender.com/health |
| **CI runs** | https://github.com/Miskat-SE/functional-testing-2405207/actions |
| **Student ID** | 2405207 |

Every push is linted and tested on Python 3.10, 3.11 and 3.12. Only a push to `main` that passes every test is deployed, and a smoke test then confirms the live site is running that exact commit.

---

## Contents

- [Project layout](#project-layout)
- [Setup](#setup)
- [Running the tests](#running-the-tests)
- [Test design](#test-design)
- [Suspected bugs in target.py](#suspected-bugs-in-targetpy)
- [Frontend](#frontend)
- [CI/CD pipeline](#cicd-pipeline)
- [Deployment (Render)](#deployment-render)
- [Branch protection and workflow](#branch-protection-and-workflow)

## Project layout

```
.
├── target.py                  # code under test (provided; not modified)
├── tests/
│   ├── test_target.py         # functional tests for all 16 functions
│   └── test_app.py            # tests for the web API and frontend
├── app.py                     # Flask app: frontend, JSON API and /health
├── templates/index.html       # frontend page
├── static/                    # frontend CSS and JavaScript
├── scripts/
│   ├── smoke_test.py          # post-deploy smoke test used by CI
│   └── mutation_test.py       # runs the tests against faulty versions of target.py
├── .github/workflows/ci.yml   # test -> deploy -> smoke-test pipeline
├── render.yaml                # Render service definition (auto-deploy off)
├── pyproject.toml             # pytest, coverage and ruff configuration
├── requirements.txt           # pinned runtime dependencies
├── requirements-dev.txt       # pinned test and lint dependencies
└── .python-version            # Python version used on Render (3.12)
```

## Setup

Requires Python 3.10 or newer.

```bash
git clone https://github.com/Miskat-SE/functional-testing-2405207.git
cd functional-testing-2405207
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

Run the frontend locally:

```bash
flask --app app run                # http://127.0.0.1:5000
```

## Running the tests

The test command from the assignment:

```bash
pytest --cov=target --cov-branch
```

The same command CI runs, which also fails below 100% coverage and writes the reports:

```bash
ruff check .
pytest --cov=target --cov-branch --cov-report=term-missing --cov-report=html --cov-fail-under=100
```

Result: **423 tests pass** (378 for `target.py`, 45 for the web app) with **100% line and branch coverage** of `target.py` (59 statements, 26 branches) on Python 3.10, 3.11 and 3.12. There are no `skip`, `xfail` or other hidden failures.

Check that the tests catch faulty versions of `target.py` (mutation testing):

```bash
python scripts/mutation_test.py
```

This builds 165 faulty versions of `target.py` (for example `>=` changed to `>`, `/` to `//`, `&` to `|`, a guard clause removed, a constant changed by one, `.strip()` dropped or an error message changed) and runs the suite against each one. **All 164 non-equivalent mutants are caught.** The one remaining mutant (`range(1, n + 1)` changed to `range(2, n + 1)` in `factorial`) is equivalent: multiplying by 1 changes nothing, so no test can tell it apart.

## Test design

`tests/test_target.py` covers four kinds of input for every function: valid values, boundary values, invalid values and wrong types. All of them use `pytest.mark.parametrize`.

| Rule | How it is applied |
|---|---|
| Exact exception class | `pytest.raises(ValueError)` etc., never a parent class such as `Exception`. |
| Messages | Messages written in `target.py` are matched in full (`match=r"^list is empty$"`). Python's own messages change between versions (3.12 and 3.14 word several differently), so only a stable fragment of those is matched. |
| Result types | Checked wherever the type is part of the contract: `bool` results use `is True`/`is False`, `divide` must return `float`, `swap` must return `tuple`, `power(2, 3)` must return `int`, and so on. |
| `pytest.approx` | Used only for inexact floats (`divide(1, 3)`, `square_root(2)`, `average([0.1, 0.2, 0.3])`). Rounded or exactly representable results use `==`, so a missing `round()` is caught. |
| Boundaries | Tested on both sides of each edge: age 17/18/19, year 0/1, `x = 0` vs `x = -0.0001`, `n = 0`, empty vs one-element lists, tuples of length 1/2/3. |
| Side effects | Inputs are checked to be unchanged after the call (lists, sets, dicts). |
| Current behaviour of suspected bugs | Tests whose names end in `characterises_current_behaviour` pin down what the code does today for the bugs listed below, so any change is noticed. They pass against the original `target.py`. |

Examples of faulty versions the suite catches: `age > 18`, `year < 0`, `x <= 0`, `a // b`, `set_a | set_b`, `min(numbers)`, `range(1, n)`, `sum(numbers) / (len(numbers) - 1)`, `round(..., 1)`, a missing `.lower()` or `.strip()`, `math.pow` (returns `float`), `statistics.mean` (returns `int`), `set.intersection` (accepts lists), and `prices.get(item)` checks that treat a price of `0` or `None` as missing.

> Note: the `target.py` handed out was a PDF export of the code (a Google Docs render saved with a `.py` extension). The file in this repository is that code copied exactly. The only change is that comment and string lines broken across two lines by the PDF layout are joined back into one. Logic, names and messages are unchanged.

## Suspected bugs in target.py

`target.py` is not modified. These are places where the code either does not match its own comment or lets wrong input through. Each one is shown by a test in `tests/test_target.py`.

| # | Function | Suspected bug | Evidence |
|---|---|---|---|
| 1 | `is_adult` | The comment says "Integer", but there is no type check. `is_adult(True)` returns `False` (bool is treated as age 1) and floats are accepted. Non-numbers fail with Python's comparison `TypeError` instead of a clear message. There is no upper limit (`is_adult(150)` is `True`). | `is_adult(True) is False`, `is_adult("18")` → `TypeError: '<' not supported…` |
| 2 | `celsius_to_fahrenheit` | No input validation: values below absolute zero are accepted (`-300` → `-508.0`), and `True` is converted as `1` (`33.8`). A string fails with a confusing `TypeError` about the `/` operator. | `celsius_to_fahrenheit(-300) == -508.0` |
| 3 | `count_vowels` | Only the ASCII letters `aeiou` are counted, so accented vowels are ignored (`"éàü"` → `0`, `"café"` → `1`). | `count_vowels("éàü") == 0` |
| 4 | `greet` | A non-string name (`greet(123)`) raises `AttributeError: 'int' object has no attribute 'strip'` instead of a `TypeError` like the other functions. Any whitespace (tabs, newlines) counts as blank, not only spaces as the comment says. | `greet(123)` → `AttributeError` |
| 5 | `find_max` | The comment says "List" of numbers, but any sized iterable is accepted: `find_max("abc")` returns `'c'`, sets and dicts work. A generator is rejected (`has no len()`) even though `max()` supports it. Every empty input gives the message "list is empty". | `find_max("abc") == "c"` |
| 6 | `get_price` | `prices` is not checked to be a dict. With a list, the `in` check passes and indexing then fails: `get_price(["apple"], "apple")` → `TypeError: list indices must be integers…`. An unhashable item gives `TypeError` instead of `KeyError`. | `get_price(["apple"], "apple")` → `TypeError` |
| 7 | `swap` | The comment says "Tuple", but any length-2 sequence is accepted (`swap("ab")` → `('b', 'a')`). A 2-key dict raises `KeyError: 1` and a 2-item set raises `TypeError: not subscriptable`, which leaks internal details instead of a clear error. | `swap({"a": 1, "b": 2})` → `KeyError` |
| 8 | `common_items` | No type validation: lists fail with `TypeError: unsupported operand type(s) for &`. Two frozensets return a `frozenset`, not a `set`. | `type(common_items(frozenset(), frozenset())) is frozenset` |
| 9 | `is_leap_year` | Floats and bools are accepted: `is_leap_year(2000.0)` is `True`, and `is_leap_year(True)` is treated as year 1. Gregorian rules are applied to every year, including years before 1582 when the calendar did not exist. | `is_leap_year(2000.0) is True` |
| 10 | `to_int` | Floats are truncated toward zero without warning (`3.9` → `3`, `-3.9` → `-3`). `inf` raises `OverflowError` and `nan` raises `ValueError`, neither of which is documented. Strings like `" 42 "`, `"1_000"` and `b"12"` are accepted. | `to_int(3.9) == 3`, `to_int(math.inf)` → `OverflowError` |
| 11 | `divide` | `False` counts as zero (`divide(1, False)` → `ZeroDivisionError`) because bools are not rejected. | `divide(1, False)` raises |
| 12 | `power` | A negative base with a fractional exponent silently returns a complex number (`power(-8, 1/3)` → `(1+1.732j)`, not `-2.0`). `power(0, -1)` raises `ZeroDivisionError` with Python's message, which differs between versions and from `divide`'s message. Float overflow raises `OverflowError`. There is no limit on huge integer exponents, so `power(10, 10**9)` can hang the process. | `type(power(-8, 1/3)) is complex` |
| 13 | `square_root` | `square_root(-0.0)` returns `-0.0` (the sign leaks through because `-0.0 < 0` is `False`). `nan` is not rejected and returns `nan`. | `math.copysign(1, square_root(-0.0)) == -1` |
| 14 | `factorial` | Whole-number floats such as `3.0` are rejected with Python's `range()` error (`'float' object cannot be interpreted as an integer`) instead of a clear message. `factorial(True)` returns `1`. There is no upper limit (very large `n` is slow). | `factorial(3.0)` → `TypeError` |
| 15 | `average` | The sum can overflow even when the average cannot: `average([1e308, 1e308])` returns `inf`, but the true average is `1e308`. Results for inexact floats differ by one bit between Python versions, because Python 3.12 changed `sum()` to compensated summation. A generator is rejected. | `average([1e308, 1e308]) == inf` |
| 16 | `invert` | No bug found. Only `True` and `False` are accepted. | — |

## Frontend

The web page (`/`) has a card for each of the 16 functions. Each card has input fields, one-click example buttons (valid, boundary, invalid, wrong type) and a result panel. The panel shows the call, the returned value and its Python type, or the exception class and message. "Run every example" runs all examples, and the call history keeps the last 50 calls. The footer and header show the deployed commit SHA, read from `/health`.

Inputs are Python literals (`42`, `'text'`, `None`, `[1, 2]`, `(1, 2)`, `{1, 2}`, `{'apple': 1.25}`). They are parsed with `ast.literal_eval`, which never runs code. Inputs are limited to 500 characters, and very large `power`/`factorial` inputs are refused so the free server cannot be hung.

JSON API:

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | `{"status": "ok", "commit": "<deployed SHA>", "python": "3.12.x"}` |
| `GET` | `/api/functions` | Names, parameters and examples for all 16 functions |
| `POST` | `/api/run` | Body `{"function": "divide", "args": ["10", "4"]}` returns `{"ok": true, "result": "2.5", "result_type": "float", ...}`. An exception from `target.py` returns `{"ok": false, "error": {"type": "ZeroDivisionError", "message": "cannot divide by zero"}}`. Bad requests return HTTP 400. |

## CI/CD pipeline

`.github/workflows/ci.yml` runs on every push and on every pull request to `main`. It has three jobs and one gate:

```
push to main ──► test ──(all pass?)──yes──► deploy ──► smoke-test ──► change is live
                 lint + pytest      │                  (needs: test)    waits for new SHA,
                 Python 3.10–3.12   no                 deploy hook       checks 3 live requests
                                    ▼                  from a secret
                           pipeline stops: deploy skipped, live site unchanged
```

1. **`test`** (matrix: Python 3.10, 3.11, 3.12, with pip caching). Runs `ruff check`, then `pytest` with `--cov-fail-under=100`, so the job fails if line or branch coverage of `target.py` drops below 100%. The coverage report (XML, HTML and JUnit) is uploaded as an artifact for each Python version.
2. **`deploy`** (`needs: test`). Runs only for pushes to `main` (`if: github.event_name == 'push' && github.ref == 'refs/heads/main'`). It calls the Render deploy hook stored in the secret `RENDER_DEPLOY_HOOK_URL` and passes `&ref=<commit SHA>` so Render builds exactly the tested commit.
3. **`smoke-test`** (`needs: deploy`). Runs `scripts/smoke_test.py`, which polls `/health` until it reports the new commit SHA. It then checks three live requests: the page renders all 16 functions and the SHA, `divide(10, 4)` returns `2.5`, and `divide(1, 0)` reports `ZeroDivisionError`.

If any test fails, `deploy` and `smoke-test` are skipped and the live site stays on the last good commit.

## Deployment (Render)

- Service: Render web service `functional-testing-2405207` (free plan), Python 3.12 (`.python-version`).
- Build: `pip install -r requirements.txt`. Start: `gunicorn app:app --workers 2 --timeout 60`. Health check: `/health`.
- **Auto-Deploy: Off.** Render never deploys on its own. Only the `deploy` job does, after the tests pass.
- GitHub secret `RENDER_DEPLOY_HOOK_URL` holds the deploy hook. It is never committed.
- Optional repository variable `LIVE_URL` overrides the live URL if Render assigns a different one.
- `/health` returns `RENDER_GIT_COMMIT`, the commit Render actually built, which the footer shows.

Note: free Render services sleep when idle, so the first request after a pause can take up to about a minute.

## Branch protection and workflow

- `main` is protected. Changes arrive through pull requests, and the status checks `test (3.10)`, `test (3.11)` and `test (3.12)` must pass before merging.
- Features were built on branches and merged through pull requests: `feature/functional-tests`, `feature/ci-workflow`, `feature/frontend` and `feature/deploy-pipeline`.
- The Actions history includes one red run from a failing test followed by the green fix.
