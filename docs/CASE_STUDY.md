# Case study: trustworthy retail operations metrics

## Problem

Order, inventory, and fulfillment extracts often arrive as operational files with inconsistent values. Building a dashboard directly on those files can turn source defects into executive metrics.

## Users and decisions

- Operations managers prioritize stores and product lines.
- Inventory planners identify products at or below reorder thresholds.
- Finance analysts review revenue and margin.
- Data engineers investigate rejected records and reconciliation results.

## Technical decisions

1. Validate before loading so rejected records never silently enter KPIs.
2. Use `order_id` as the natural key so overlapping files never duplicate orders; keep a content-hash batch identifier for lineage.
3. Preserve rejection reasons as queryable evidence.
4. Separate the order fact table from the KPI consumption views.
5. Use decimal arithmetic for business calculations.

## Verified result

The bundled synthetic batch contains ten source rows: eight accepted and two rejected. The automated test suite (see `tests/`) verifies reconciliation, revenue, margin, low-stock logic, decision views, reject persistence, HTML/JSON export, and the interactive Streamlit dashboard. The generated dashboard reports three store performance records and four inventory action items.

## Limitations and next production steps

The portfolio version is a single-process batch. A production design would add orchestration, cloud object storage, slowly changing dimensions, incremental merge logic, access control, observability, alert routing, and BI semantic models.
