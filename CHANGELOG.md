# Changelog

All notable changes to this portfolio project are documented in this file.

The project follows semantic versioning for public portfolio releases. Version numbers describe the repository's software baseline; they do not indicate production readiness of the platform.

## [Unreleased]

### Fixed

- Idempotency is now per `order_id` (upsert) instead of per file hash; overlapping files no longer duplicate orders or revenue
- Reject duplicate `order_id` within a file, empty `store_id`/`product_id`/`category`, and truncated or malformed rows (with reasons) instead of aborting
- `run()` executes in a single transaction and rolls back on failure
- Docker image runs as a non-root user; added `.dockerignore`
- Documentation no longer claims raw/dimension tables or reconciliation checks that do not exist

### Changed

- CI now runs `ruff` and `mypy`, declares least-privilege `permissions`, and enforces `--cov-fail-under=85` (branch coverage, including `dashboard.py`)
- `pytest` moved out of the runtime `requirements.txt` into `requirements-dev.txt`; `streamlit>=1.49` (first release accepting `width="stretch"`) and `pandas>=2.2,<4`
- Money in the HTML/JSON export and dashboard stays `Decimal` instead of `float`
- `reorder_queue` breaks same-day ties deterministically (`order_id`) and has a total ordering
- Dockerfile gains a `HEALTHCHECK`; the DuckDB file lives on the `retail_db` volume (`RETAIL_OPS_DATABASE`), and `./data` is mounted read-only
- `.gitignore` covers coverage output, egg-info, and ruff/mypy caches; `CONTRIBUTING.md` and `SECURITY.md` expanded

### Added

- Tests for missing columns, header-only files, overlapping batches, same-day ties, CLI entry points, HTML escaping, and the Streamlit dashboard (empty state, filtering)

## [0.1.0] — 2026-08-27

Version aligned with `pyproject.toml` (previously labelled 1.0.0).

### Added

- Batch ingestion with deterministic (file-hash) batch identifiers
- Explicit schema and domain validation before loading, with reject evidence
- DuckDB fact table and reject table
- Revenue, margin, fulfillment, and low-stock KPI mart
- Store-performance and inventory reorder decision views
- Run summary with accepted/rejected counts and totals
- Interactive Python/Streamlit operations dashboard
- Self-contained HTML and JSON evidence exports
- Reproducible CLI pipeline (`retail_ops.pipeline`, `retail_ops.report`)
- Unit and integration test suite (`pytest`)

### Known limitations

- No managed secrets, orchestration, or object storage
- No access controls, observability, data contracts, or recovery procedures
- Synthetic data only; no employer, payment, personal, or production data
