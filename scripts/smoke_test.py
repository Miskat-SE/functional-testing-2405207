"""Post-deploy smoke test for the live site.

1. Waits until GET /health reports the expected commit SHA (the new deploy is
   live), polling until a timeout.
2. Then checks three live requests:
   a. GET /                       -> page renders all 16 functions and the SHA
   b. POST /api/run divide(10, 4) -> ok, result 2.5 (float)
   c. POST /api/run divide(1, 0)  -> ZeroDivisionError reported to the user

Usage:
    python scripts/smoke_test.py --url https://example.onrender.com --sha <commit>

Only the standard library is used so the CI job needs no pip install.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

USER_AGENT = "functional-testing-smoke-test/1.0"


def http(method: str, url: str, payload: dict | None = None, timeout: float = 60):
    data = None
    headers = {"User-Agent": USER_AGENT, "Cache-Control": "no-cache"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8").strip()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def sha_matches(live: str, expected: str) -> bool:
    live, expected = live.strip().lower(), expected.strip().lower()
    if not live or not expected or live == "unknown":
        return False
    return live.startswith(expected) or expected.startswith(live)


def wait_for_sha(base: str, expected: str, timeout: float, interval: float) -> None:
    deadline = time.monotonic() + timeout
    attempt = 0
    while True:
        attempt += 1
        live = "<no response>"
        try:
            status, body = http("GET", f"{base}/health")
            if status == 200:
                live = json.loads(body).get("commit", "")
                if sha_matches(live, expected):
                    print(f"[wait] attempt {attempt}: live commit {live} matches")
                    return
            else:
                live = f"HTTP {status}"
        except (OSError, ValueError) as error:  # network error or bad JSON
            live = f"{type(error).__name__}: {error}"
        remaining = deadline - time.monotonic()
        print(f"[wait] attempt {attempt}: live={live!r}, want={expected[:7]}")
        if remaining <= 0:
            raise SystemExit(
                f"FAIL: /health did not report commit {expected} within {timeout:.0f}s"
            )
        time.sleep(min(interval, max(remaining, 1)))


def check(name: str, condition: bool, detail: str) -> bool:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")
    return condition


def run_checks(base: str, expected: str) -> bool:
    results = []

    status, html = http("GET", f"{base}/")
    cards = html.count('class="card"')
    results.append(
        check(
            "GET / renders the frontend",
            status == 200
            and cards == 16
            and 'id="commit-sha"' in html
            and expected[:7] in html,
            f"HTTP {status}, {cards} function cards",
        )
    )

    status, body = http(
        "POST", f"{base}/api/run", {"function": "divide", "args": ["10", "4"]}
    )
    data = json.loads(body) if status == 200 else {}
    results.append(
        check(
            "POST /api/run divide(10, 4)",
            data.get("ok") is True
            and data.get("result") == "2.5"
            and data.get("result_type") == "float",
            f"HTTP {status}, body={body[:120]}",
        )
    )

    status, body = http(
        "POST", f"{base}/api/run", {"function": "divide", "args": ["1", "0"]}
    )
    data = json.loads(body) if status == 200 else {}
    results.append(
        check(
            "POST /api/run divide(1, 0) reports the error",
            data.get("ok") is False
            and data.get("error", {}).get("type") == "ZeroDivisionError"
            and data.get("error", {}).get("message") == "cannot divide by zero",
            f"HTTP {status}, body={body[:120]}",
        )
    )
    return all(results)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the live deployment.")
    parser.add_argument("--url", required=True, help="base URL of the live site")
    parser.add_argument("--sha", required=True, help="commit SHA that must be live")
    parser.add_argument("--timeout", type=float, default=900, help="seconds")
    parser.add_argument("--interval", type=float, default=15, help="seconds")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    print(f"Smoke testing {base} for commit {args.sha}")
    wait_for_sha(base, args.sha, args.timeout, args.interval)
    if run_checks(base, args.sha):
        print("All smoke checks passed: the new commit is live and working.")
        return 0
    print("Smoke checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
