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
2. Generate a deterministic batch identifier from source content for reproducibility.
3. Preserve rejection reasons as queryable evidence.
4. Separate raw operational fields from the KPI consumption view.
5. Use decimal arithmetic for business calculations.

## Verified result

The bundled synthetic batch contains ten source rows: eight accepted and two rejected. Four automated tests verify reconciliation, revenue, margin, low-stock logic, decision views, reject persistence, HTML/JSON export, and the interactive Streamlit dashboard. The generated dashboard reports three store performance records and three inventory action items.

## Limitations and next production steps

The portfolio version is a single-process batch. A production design would add orchestration, cloud object storage, slowly changing dimensions, incremental merge logic, access control, observability, alert routing, and BI semantic models.
