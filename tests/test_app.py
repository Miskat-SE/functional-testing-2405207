"""Tests for the Flask frontend / API in app.py."""

import pytest

import app as app_module


@pytest.fixture()
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


def run(client, function, *args):
    return client.post("/api/run", json={"function": function, "args": list(args)})


def test_health_returns_status_and_commit(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["commit"] == app_module.app.config["COMMIT_SHA"]
    assert isinstance(body["python"], str)


def test_commit_sha_prefers_render_variable(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123def456")
    monkeypatch.setenv("GIT_COMMIT", "should-not-win")
    assert app_module.get_commit_sha() == "abc123def456"
    fresh = app_module.create_app()
    assert fresh.test_client().get("/health").get_json()["commit"] == "abc123def456"


def test_commit_sha_falls_back_to_git_commit(monkeypatch):
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    monkeypatch.setenv("GIT_COMMIT", "feedbeef")
    assert app_module.get_commit_sha() == "feedbeef"


def test_commit_sha_unknown_without_git(monkeypatch):
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    monkeypatch.delenv("GIT_COMMIT", raising=False)

    def broken_run(*args, **kwargs):
        raise OSError("git not installed")

    monkeypatch.setattr(app_module.subprocess, "run", broken_run)
    assert app_module.get_commit_sha() == "unknown"


def test_index_lists_all_sixteen_functions_and_commit(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for spec in app_module.SPECS:
        assert f'data-function="{spec.name}"' in html
    assert 'id="commit-sha"' in html
    assert app_module.app.config["COMMIT_SHA"][:7] in html


def test_functions_endpoint_matches_target_module(client):
    data = client.get("/api/functions").get_json()
    assert len(data) == 16
    assert {item["name"] for item in data} == set(app_module.SPEC_BY_NAME)
    assert sum(item["category"] == "Mathematics" for item in data) == 5


@pytest.mark.parametrize(
    ("function", "args", "result", "result_type"),
    [
        ("is_adult", ["18"], "True", "bool"),
        ("celsius_to_fahrenheit", ["37"], "98.6", "float"),
        ("count_vowels", ["'Hello World'"], "3", "int"),
        ("invert", ["False"], "True", "bool"),
        ("greet", ["'  Alice '"], "'Hello, Alice!'", "str"),
        ("greet", [""], "'Hello, Guest!'", "str"),  # blank -> default None
        ("find_max", ["[3, 9, 2]"], "9", "int"),
        ("get_price", ["{'apple': 1.25}", "'apple'"], "1.25", "float"),
        ("swap", ["(1, 2)"], "(2, 1)", "tuple"),
        ("common_items", ["{1, 2, 3}", "{2, 3, 4}"], "{2, 3}", "set"),
        ("is_leap_year", ["2000"], "True", "bool"),
        ("to_int", ["'42'"], "42", "int"),
        ("divide", ["7", "2"], "3.5", "float"),
        ("power", ["2", "10"], "1024", "int"),
        ("square_root", ["16"], "4.0", "float"),
        ("factorial", ["5"], "120", "int"),
        ("average", ["[1, 2]"], "1.5", "float"),
    ],
)
def test_run_returns_result_and_type(client, function, args, result, result_type):
    response = run(client, function, *args)
    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert body["result"] == result
    assert body["result_type"] == result_type


@pytest.mark.parametrize(
    ("function", "args", "error_type", "message"),
    [
        ("is_adult", ["-1"], "ValueError", "age cannot be negative"),
        ("count_vowels", ["5"], "TypeError", "text must be a string"),
        ("get_price", ["{}", "'banana'"], "KeyError", "'banana not found'"),
        ("swap", ["(1,)"], "ValueError", "pair must have exactly 2 values"),
        ("divide", ["1", "0"], "ZeroDivisionError", "cannot divide by zero"),
        ("to_int", ["True"], "TypeError", "bool is not allowed"),
        ("average", ["[]"], "ValueError", "list is empty"),
    ],
)
def test_run_reports_function_errors(client, function, args, error_type, message):
    response = run(client, function, *args)
    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is False
    assert body["error"] == {"type": error_type, "message": message}


def test_run_shows_the_call(client):
    body = run(client, "divide", "10", "4").get_json()
    assert body["call"] == "divide(10, 4)"


def test_run_unknown_function_is_404(client):
    response = run(client, "os_system", "'ls'")
    assert response.status_code == 404
    assert response.get_json()["error"]["type"] == "NotFound"


@pytest.mark.parametrize(
    ("payload", "fragment"),
    [
        ({"function": "divide", "args": ["1"]}, "takes 2 argument(s), got 1"),
        ({"function": "divide", "args": "1, 2"}, "'args' must be a list"),
        ({"function": "divide", "args": ["1", ""]}, "argument 'b' is required"),
        ({"function": "divide", "args": ["1", 2]}, "must be sent as a string"),
        ({"function": "count_vowels", "args": ["hello"]}, "not a valid Python"),
        ({"function": "count_vowels", "args": ["__import__('os')"]}, "not a valid"),
        ({"function": "count_vowels", "args": ["'" + "a" * 600 + "'"]}, "longer"),
        ({"function": "power", "args": ["10", "10**9"]}, "not a valid"),
        ({"function": "power", "args": ["10", "100000"]}, "exponent is limited"),
        ({"function": "factorial", "args": ["100000"]}, "n is limited"),
    ],
)
def test_run_rejects_bad_input_with_400(client, payload, fragment):
    response = client.post("/api/run", json=payload)
    assert response.status_code == 400
    body = response.get_json()
    assert body["ok"] is False
    assert body["error"]["type"] == "InputError"
    assert fragment in body["error"]["message"]


def test_run_requires_json_object(client):
    response = client.post("/api/run", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_power_limit_allows_small_bases_with_big_exponents(client):
    body = run(client, "power", "1", "100000").get_json()
    assert body["ok"] is True
    assert body["result"] == "1"


def test_huge_integer_result_is_described_not_crashing(client):
    body = run(client, "factorial", "5000").get_json()
    assert body["ok"] is True
    assert body["result_type"] == "int"
