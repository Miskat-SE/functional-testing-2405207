"""Flask web frontend and JSON API for the functions in target.py.

Routes
------
GET  /                 the interactive web page
GET  /api/functions    metadata for all 16 functions (parameters, examples)
POST /api/run          run one function: {"function": "divide", "args": ["10", "2"]}
GET  /health           liveness probe that also returns the deployed commit SHA

Arguments are sent as Python literals (``42``, ``'text'``, ``[1, 2]``,
``None`` ...) and parsed with ``ast.literal_eval``, which never executes code.
"""

from __future__ import annotations

import ast
import os
import platform
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable

from flask import Flask, jsonify, render_template, request

import target

MAX_ARG_LENGTH = 500
MAX_POWER_EXPONENT = 10_000
MAX_FACTORIAL_N = 5_000


@dataclass(frozen=True)
class FunctionSpec:
    name: str
    func: Callable[..., Any]
    category: str
    summary: str
    params: list[str]
    examples: list[tuple[str, list[str]]] = field(default_factory=list)
    optional: frozenset[str] = frozenset()


SPECS: list[FunctionSpec] = [
    FunctionSpec(
        "is_adult",
        target.is_adult,
        "Data types",
        "Integer: True if age is 18 or more. Negative age raises ValueError.",
        ["age"],
        [
            ("valid", ["30"]),
            ("boundary", ["18"]),
            ("boundary", ["17"]),
            ("invalid", ["-1"]),
            ("wrong type", ["'18'"]),
        ],
    ),
    FunctionSpec(
        "celsius_to_fahrenheit",
        target.celsius_to_fahrenheit,
        "Data types",
        "Float: convert Celsius to Fahrenheit, rounded to 2 decimals.",
        ["celsius"],
        [
            ("valid", ["37"]),
            ("boundary", ["-40"]),
            ("valid", ["36.6"]),
            ("wrong type", ["'hot'"]),
        ],
    ),
    FunctionSpec(
        "count_vowels",
        target.count_vowels,
        "Data types",
        "String: count vowels (a, e, i, o, u), ignoring case.",
        ["text"],
        [
            ("valid", ["'Hello World'"]),
            ("boundary", ["''"]),
            ("valid", ["'AEIOU'"]),
            ("wrong type", ["123"]),
        ],
    ),
    FunctionSpec(
        "invert",
        target.invert,
        "Data types",
        "Boolean: return the opposite of flag. Non-bool raises TypeError.",
        ["flag"],
        [("valid", ["True"]), ("valid", ["False"]), ("wrong type", ["1"])],
    ),
    FunctionSpec(
        "greet",
        target.greet,
        "Data types",
        "None: greet by name, or 'Guest' if name is None, empty or spaces. "
        "Leave the field blank to use the default.",
        ["name"],
        [
            ("valid", ["'  Alice  '"]),
            ("boundary", ["None"]),
            ("boundary", ["'   '"]),
            ("wrong type", ["42"]),
        ],
        optional=frozenset({"name"}),
    ),
    FunctionSpec(
        "find_max",
        target.find_max,
        "Data types",
        "List: return the largest number. Empty list raises ValueError.",
        ["numbers"],
        [
            ("valid", ["[3, 9, 2]"]),
            ("boundary", ["[-5]"]),
            ("invalid", ["[]"]),
            ("wrong type", ["None"]),
        ],
    ),
    FunctionSpec(
        "get_price",
        target.get_price,
        "Data types",
        "Dictionary: return the price of item. Missing item raises KeyError.",
        ["prices", "item"],
        [
            ("valid", ["{'apple': 1.25, 'bread': 2}", "'apple'"]),
            ("boundary", ["{'water': 0}", "'water'"]),
            ("invalid", ["{'apple': 1.25}", "'banana'"]),
            ("wrong type", ["None", "'apple'"]),
        ],
    ),
    FunctionSpec(
        "swap",
        target.swap,
        "Data types",
        "Tuple: return the two values swapped. Not exactly 2 values raises ValueError.",
        ["pair"],
        [
            ("valid", ["(1, 2)"]),
            ("valid", ["('a', 'b')"]),
            ("invalid", ["(1, 2, 3)"]),
            ("wrong type", ["None"]),
        ],
    ),
    FunctionSpec(
        "common_items",
        target.common_items,
        "Data types",
        "Set: return the items found in both sets.",
        ["set_a", "set_b"],
        [
            ("valid", ["{1, 2, 3}", "{2, 3, 4}"]),
            ("boundary", ["set()", "{1}"]),
            ("wrong type", ["[1, 2]", "[2, 3]"]),
        ],
    ),
    FunctionSpec(
        "is_leap_year",
        target.is_leap_year,
        "Data types",
        "Date: True if year is a leap year. Year below 1 raises ValueError.",
        ["year"],
        [
            ("valid", ["2024"]),
            ("boundary", ["1900"]),
            ("boundary", ["2000"]),
            ("invalid", ["0"]),
            ("wrong type", ["'2024'"]),
        ],
    ),
    FunctionSpec(
        "to_int",
        target.to_int,
        "Data types",
        "Type conversion: convert value to int. A bool raises TypeError.",
        ["value"],
        [
            ("valid", ["'42'"]),
            ("valid", ["3.9"]),
            ("invalid", ["'abc'"]),
            ("wrong type", ["True"]),
        ],
    ),
    FunctionSpec(
        "divide",
        target.divide,
        "Mathematics",
        "Return a / b. Dividing by zero raises ZeroDivisionError.",
        ["a", "b"],
        [
            ("valid", ["10", "4"]),
            ("valid", ["1", "3"]),
            ("invalid", ["5", "0"]),
            ("wrong type", ["'10'", "2"]),
        ],
    ),
    FunctionSpec(
        "power",
        target.power,
        "Mathematics",
        "Return base raised to exponent.",
        ["base", "exponent"],
        [
            ("valid", ["2", "10"]),
            ("boundary", ["0", "0"]),
            ("valid", ["2", "-1"]),
            ("invalid", ["0", "-1"]),
            ("wrong type", ["'2'", "3"]),
        ],
    ),
    FunctionSpec(
        "square_root",
        target.square_root,
        "Mathematics",
        "Return the square root of x. Negative x raises ValueError.",
        ["x"],
        [
            ("valid", ["16"]),
            ("boundary", ["0"]),
            ("valid", ["2"]),
            ("invalid", ["-4"]),
            ("wrong type", ["'9'"]),
        ],
    ),
    FunctionSpec(
        "factorial",
        target.factorial,
        "Mathematics",
        "Return n factorial. Negative n raises ValueError.",
        ["n"],
        [
            ("valid", ["5"]),
            ("boundary", ["0"]),
            ("invalid", ["-1"]),
            ("wrong type", ["2.5"]),
        ],
    ),
    FunctionSpec(
        "average",
        target.average,
        "Mathematics",
        "Return the average of a list. Empty list raises ValueError.",
        ["numbers"],
        [
            ("valid", ["[1, 2, 3, 4]"]),
            ("boundary", ["[7]"]),
            ("invalid", ["[]"]),
            ("wrong type", ["['a', 'b']"]),
        ],
    ),
]
SPEC_BY_NAME = {spec.name: spec for spec in SPECS}


class InputError(Exception):
    """Raised when the request itself is invalid (not the function call)."""


def get_commit_sha() -> str:
    """Return the commit SHA of the running code.

    Render sets RENDER_GIT_COMMIT for every deploy. GIT_COMMIT can be set by
    any other host. Locally we fall back to ``git rev-parse HEAD``.
    """
    for key in ("RENDER_GIT_COMMIT", "GIT_COMMIT"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        return completed.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def parse_argument(param: str, text: Any) -> Any:
    if not isinstance(text, str):
        raise InputError(f"argument '{param}' must be sent as a string")
    if len(text) > MAX_ARG_LENGTH:
        raise InputError(
            f"argument '{param}' is longer than {MAX_ARG_LENGTH} characters"
        )
    try:
        return ast.literal_eval(text.strip())
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        raise InputError(
            f"argument '{param}' is not a valid Python literal: {text!r}. "
            "Strings need quotes, e.g. 'hello'."
        ) from None


def check_resource_limits(spec: FunctionSpec, args: list[Any]) -> None:
    """Refuse inputs that would hang a small free-tier server."""
    if spec.name == "power":
        base, exponent = args
        if (
            isinstance(exponent, int)
            and not isinstance(exponent, bool)
            and abs(exponent) > MAX_POWER_EXPONENT
            and isinstance(base, (int, float))
            and abs(base) > 1
        ):
            raise InputError(
                f"exponent is limited to ±{MAX_POWER_EXPONENT} on the live demo"
            )
    if spec.name == "factorial":
        (n,) = args
        if isinstance(n, int) and n > MAX_FACTORIAL_N:
            raise InputError(f"n is limited to {MAX_FACTORIAL_N} on the live demo")


def describe(value: Any) -> str:
    try:
        return repr(value)
    except ValueError:  # int too large to print (Python 3.11+ digit limit)
        return f"<{type(value).__name__} with more than 4300 digits>"


def run_function(name: str, raw_args: Any) -> dict[str, Any]:
    spec = SPEC_BY_NAME.get(name)
    if spec is None:
        raise LookupError(name)
    if not isinstance(raw_args, list):
        raise InputError("'args' must be a list of strings")
    if len(raw_args) != len(spec.params):
        raise InputError(
            f"{name} takes {len(spec.params)} argument(s), got {len(raw_args)}"
        )

    args: list[Any] = []
    for param, raw in zip(spec.params, raw_args, strict=True):
        if isinstance(raw, str) and raw.strip() == "":
            if param in spec.optional:
                continue  # use the function's default value
            raise InputError(f"argument '{param}' is required")
        args.append(parse_argument(param, raw))

    if len(args) == len(spec.params):
        check_resource_limits(spec, args)

    call = f"{name}({', '.join(describe(a) for a in args)})"
    try:
        result = spec.func(*args)
    except Exception as exc:  # report every error raised by target.py
        return {
            "ok": False,
            "function": name,
            "call": call,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
    return {
        "ok": True,
        "function": name,
        "call": call,
        "result": describe(result),
        "result_type": type(result).__name__,
    }


def create_app() -> Flask:
    app = Flask(__name__)
    app.json.sort_keys = False
    commit = get_commit_sha()
    app.config["COMMIT_SHA"] = commit

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            specs=SPECS,
            commit=app.config["COMMIT_SHA"],
            repo_url=os.environ.get(
                "REPO_URL", "https://github.com/Miskat-SE/functional-testing-2405207"
            ),
        )

    @app.get("/api/functions")
    def list_functions():
        return jsonify(
            [
                {
                    "name": spec.name,
                    "category": spec.category,
                    "summary": spec.summary,
                    "params": spec.params,
                    "optional": sorted(spec.optional),
                    "examples": [
                        {"label": label, "args": args} for label, args in spec.examples
                    ],
                }
                for spec in SPECS
            ]
        )

    @app.post("/api/run")
    def run():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _bad_request("request body must be a JSON object")
        name = payload.get("function")
        try:
            return jsonify(run_function(name, payload.get("args", [])))
        except LookupError:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": {
                            "type": "NotFound",
                            "message": f"unknown function: {name!r}",
                        },
                    }
                ),
                404,
            )
        except InputError as exc:
            return _bad_request(str(exc))

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "commit": app.config["COMMIT_SHA"],
                "python": platform.python_version(),
            }
        )

    return app


def _bad_request(message: str):
    body = {"ok": False, "error": {"type": "InputError", "message": message}}
    return jsonify(body), 400


app = create_app()

if __name__ == "__main__":  # pragma: no cover - local development only
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
