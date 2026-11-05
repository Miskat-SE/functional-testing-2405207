# functional-testing-2405207

[![CI](https://github.com/Miskat-SE/functional-testing-2405207/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Miskat-SE/functional-testing-2405207/actions/workflows/ci.yml)

Functional testing, CI/CD and live deployment for `target.py` (16 functions: 11 data-type, 5 mathematics).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Running the tests

```bash
pytest --cov=target --cov-branch
```
