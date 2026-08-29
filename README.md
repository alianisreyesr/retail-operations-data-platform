# Retail Operations Data Platform

[![CI](https://github.com/alianisreyesr/retail-operations-data-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/alianisreyesr/retail-operations-data-platform/actions/workflows/ci.yml)
[![CodeQL](https://github.com/alianisreyesr/retail-operations-data-platform/actions/workflows/codeql.yml/badge.svg)](https://github.com/alianisreyesr/retail-operations-data-platform/actions/workflows/codeql.yml)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-analytics-FFF000?style=flat-square&logo=duckdb&logoColor=black)
![Streamlit](https://img.shields.io/badge/Streamlit-dashboard-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-2E7D32?style=flat-square)

**Data Engineering · Analytics Engineering · Retail Operations · Decision Support**

A production-minded analytics pipeline that converts synthetic retail orders into tested dimensional models and decision-ready inventory metrics.

[Quick start](#quick-start) · [Case study](docs/CASE_STUDY.md) · [Architecture](docs/ARCHITECTURE.md) · [Source](https://github.com/alianisreyesr/retail-operations-data-platform)

> **Data boundary:** Every customer, product, order, and location is fictional. This portfolio project contains no employer, payment, personal, or production data.

## Portfolio preview

![Synthetic retail operations dashboard with revenue, margin, store performance, and inventory action queue](docs/assets/operations-dashboard.png)

The dashboard is generated from the DuckDB decision views; it is not a manually maintained mockup.

## Business outcome

Retail operations teams need one trustworthy view of revenue, demand, inventory pressure, and fulfillment performance. This project demonstrates how raw operational files become quality-checked analytical tables rather than an unreviewed dashboard export.

| Consumer | Decision supported |
|---|---|
| Operations manager | Which stores and products need attention? |
| Inventory planner | Which SKUs are below reorder level? |
| Finance analyst | What revenue and margin were generated? |
| Data team | Did source quality and reconciliation checks pass? |

## What it demonstrates

- Incremental-style ingestion with deterministic batch identifiers
- Explicit schema and domain validation before loading
- DuckDB raw, dimension, and fact tables
- Revenue, margin, fulfillment, and low-stock metrics
- Store-performance and inventory reorder decision views
- Reject records with human-readable quality reasons
- Source-to-target reconciliation and automated tests
- Interactive Streamlit dashboard plus self-contained HTML and JSON evidence exports
- Reproducible CLI execution and CI-ready quality gates

## Architecture

```mermaid
flowchart LR
  A["Synthetic CSV sources"] --> B["Validation and batch controls"]
  B -->|accepted| C["DuckDB raw layer"]
  B -->|rejected| D["Quality reject evidence"]
  C --> E["Dimensions and order fact"]
  E --> F["Operations KPI mart"]
  F --> G["Python / Streamlit dashboard"]
  F --> H["HTML and JSON evidence exports"]
```

See the [architecture notes](docs/ARCHITECTURE.md) for design decisions and production extensions.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
python -m retail_ops.pipeline --input data/orders.csv --database retail_ops.duckdb
python -m retail_ops.report --database retail_ops.duckdb --output reports/operations-dashboard.html
streamlit run dashboard.py
python -m pytest
```

Expected pipeline summary:

```text
accepted=8 rejected=2 gross_revenue=1666.00 gross_margin=698.50
dashboard=reports/operations-dashboard.html stores=3 reorder_items=4
```

## Repository structure

```mermaid
flowchart TB
  R["retail-operations-data-platform"]
  R --> D["dashboard.py — interactive Python dashboard"]
  R --> S["src/retail_ops — pipeline, rules, and report export"]
  R --> A["data — synthetic demonstration input"]
  R --> T["tests — unit and integration tests"]
  R --> O["docs — architecture and business case study"]
  R --> G[".github — automation and contribution templates"]
```

## Engineering boundary

This is a portfolio implementation, not a hosted production retail platform. Production use would require managed secrets, orchestration, object storage, access controls, observability, data contracts, recovery procedures, and environment-specific cost and performance testing.

## Target roles

Data Engineer · Analytics Engineer · BI Developer · Data Quality Engineer

---

Built by [Alianis Reyes-Reyes](https://www.linkedin.com/in/alianis-reyes-reyes/).
