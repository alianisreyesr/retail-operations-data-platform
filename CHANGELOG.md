# Changelog

All notable changes to this portfolio project are documented in this file.

The project follows semantic versioning for public portfolio releases. Version numbers describe the repository's software baseline; they do not indicate production readiness of the platform.

## [1.0.0] — 2026-08-27

### Added

- Incremental-style ingestion with deterministic batch identifiers
- Explicit schema and domain validation before loading, with reject evidence
- DuckDB raw, dimension, and fact tables
- Revenue, margin, fulfillment, and low-stock KPI mart
- Store-performance and inventory reorder decision views
- Source-to-target reconciliation checks
- Interactive Python/Streamlit operations dashboard
- Self-contained HTML and JSON evidence exports
- Reproducible CLI pipeline (`retail_ops.pipeline`, `retail_ops.report`)
- Unit and integration test suite (`pytest`)

### Known limitations

- No managed secrets, orchestration, or object storage
- No access controls, observability, data contracts, or recovery procedures
- Synthetic data only; no employer, payment, personal, or production data
