# Contributing

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Runtime dependencies live in `requirements.txt`; test and lint tooling (pytest, pytest-cov, ruff, mypy) lives in `requirements-dev.txt`. Python 3.11 or newer is required.

## Before opening a pull request

Run the same checks CI runs:

```bash
ruff check .
mypy
python -m pytest --cov        # fails below 85 % line/branch coverage
```

1. Create a focused branch and describe the business or engineering outcome.
2. Use only fictional or synthetic data.
3. Add or update tests for every behavior change. Data-quality rules need a test for both the accepted and the rejected case.
4. Update documentation (README, `docs/`, `CHANGELOG.md` under `Unreleased`) when contracts, metrics, or limitations change.
5. Do not commit secrets, credentials, customer information, proprietary data, or generated artifacts (`*.duckdb`, `reports/`, `.coverage`).
6. Write commit messages in the imperative mood and explain the why in the body when it is not obvious.

## Conventions

- Business keys (`order_id`) drive idempotency; do not key anything on file hashes alone.
- Money is handled as `Decimal`; avoid `float` for currency.
- Pipeline changes must stay transactional: a failed run must not leave partial data.
- Tests must not touch a developer's local `retail_ops.duckdb`; use `tmp_path` and the `RETAIL_OPS_DATABASE` variable.
