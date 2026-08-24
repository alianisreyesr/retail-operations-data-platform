# Architecture decisions

```mermaid
flowchart LR
  A["Synthetic order CSV"] --> B["Schema and domain validation"]
  B -->|accepted| C["DuckDB fact_orders"]
  B -->|rejected| D["Quality reject evidence"]
  C --> E["operations_kpis"]
  C --> F["store_performance"]
  C --> G["reorder_queue"]
  E --> H["Streamlit dashboard"]
  F --> H
  G --> H
  E --> I["HTML and JSON export"]
  F --> I
  G --> I
```

## Why DuckDB

DuckDB provides a reproducible analytical engine without requiring a hosted database. The transformation SQL can later move to a warehouse-oriented implementation.

## Quality contract

Every row must provide the documented columns. Numeric domains reject negative or malformed operational values. Rejected rows retain the batch identifier, business key when available, and explicit reasons.

## Idempotency

The input SHA-256 prefix is the batch identifier. Reprocessing the same source replaces its reject evidence and rebuilds the demonstration fact model deterministically.

## Production evolution

```mermaid
flowchart LR
  A["Object storage"] --> B["Orchestrated ingestion"]
  B --> C["Warehouse staging"]
  C --> D["dbt dimensions and facts"]
  D --> E["Semantic layer"]
  E --> F["Python dashboard and BI consumers"]
  G["Contracts, lineage, and observability"] -. governs .-> B
  G -. governs .-> C
  G -. governs .-> D
  G -. governs .-> E
```
