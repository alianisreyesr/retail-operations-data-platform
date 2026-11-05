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
