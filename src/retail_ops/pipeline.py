"""Load synthetic retail orders into tested DuckDB analytical models."""

from __future__ import annotations

import argparse
import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import duckdb


REQUIRED_COLUMNS = {
    "order_id",
    "order_date",
    "store_id",
    "product_id",
    "category",
    "quantity",
    "unit_price",
    "unit_cost",
    "inventory_on_hand",
    "reorder_level",
    "fulfillment_days",
}


@dataclass(frozen=True)
class PipelineSummary:
    accepted: int
    rejected: int
    gross_revenue: Decimal
    gross_margin: Decimal


def _batch_id(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def validate(row: dict[str, str]) -> list[str]:
    reasons: list[str] = []
    if not row.get("order_id", "").strip():
        reasons.append("missing_order_id")
    # order_date is cast to SQL DATE on insert (see run()); an unvalidated
    # malformed value (empty, "07/01/2026", garbage) used to reach that
    # cast and raise inside the single executemany() for the whole batch,
    # aborting every row instead of just this one.
    try:
        date.fromisoformat(row.get("order_date", "").strip())
    except ValueError:
        reasons.append("invalid_order_date")
    for field in ("quantity", "inventory_on_hand", "reorder_level", "fulfillment_days"):
        try:
            if int(row[field]) < 0:
                reasons.append(f"negative_{field}")
        except (KeyError, TypeError, ValueError):
            reasons.append(f"invalid_{field}")
    for field in ("unit_price", "unit_cost"):
        try:
            if Decimal(row[field]) < 0:
                reasons.append(f"negative_{field}")
        except (KeyError, InvalidOperation):
            reasons.append(f"invalid_{field}")
    return reasons


def run(input_path: Path, database_path: Path) -> PipelineSummary:
    batch_id = _batch_id(input_path)
    with input_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
        rows = list(reader)

    accepted: list[dict[str, str]] = []
    rejected: list[tuple[str, str]] = []
    for row in rows:
        reasons = validate(row)
        if reasons:
            rejected.append((row.get("order_id", ""), ",".join(reasons)))
        else:
            accepted.append(row)

    connection = duckdb.connect(str(database_path))
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS quality_rejects(batch_id VARCHAR, order_id VARCHAR, reasons VARCHAR)")
        connection.execute("DELETE FROM quality_rejects WHERE batch_id = ?", [batch_id])
        if rejected:
            # Same empty-list restriction as the fact_orders insert below —
            # a batch with zero rejected rows must not call executemany([]).
            connection.executemany("INSERT INTO quality_rejects VALUES (?, ?, ?)", [(batch_id, *item) for item in rejected])
        # fact_orders is append-by-batch, not drop-and-replace: re-running
        # the same input file replaces only that batch's rows (idempotent),
        # while a new input file's rows accumulate alongside prior batches
        # instead of erasing them. This is what "deterministic batch
        # identifiers" is for — DROP TABLE defeated the point of stamping
        # every row with one.
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS fact_orders(
              batch_id VARCHAR, order_id VARCHAR, order_date DATE, store_id VARCHAR,
              product_id VARCHAR, category VARCHAR, quantity INTEGER,
              unit_price DECIMAL(12,2), unit_cost DECIMAL(12,2),
              inventory_on_hand INTEGER, reorder_level INTEGER, fulfillment_days INTEGER
            )
            """
        )
        connection.execute("DELETE FROM fact_orders WHERE batch_id = ?", [batch_id])
        values = [
            (
                batch_id,
                row["order_id"], row["order_date"], row["store_id"], row["product_id"], row["category"],
                int(row["quantity"]), Decimal(row["unit_price"]), Decimal(row["unit_cost"]),
                int(row["inventory_on_hand"]), int(row["reorder_level"]), int(row["fulfillment_days"]),
            )
            for row in accepted
        ]
        if values:
            # DuckDB's executemany rejects an empty parameter-set list, so a
            # batch where every row failed validation (accepted == []) must
            # not attempt one — the DELETE above already clears any prior
            # rows for this batch_id.
            connection.executemany("INSERT INTO fact_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
        connection.execute(
            """
            CREATE OR REPLACE VIEW operations_kpis AS
            SELECT
              COUNT(DISTINCT order_id) AS order_count,
              COALESCE(SUM(quantity * unit_price), 0) AS gross_revenue,
              COALESCE(SUM(quantity * (unit_price - unit_cost)), 0) AS gross_margin,
              COUNT(*) FILTER (WHERE inventory_on_hand <= reorder_level) AS low_stock_lines,
              COALESCE(ROUND(AVG(fulfillment_days), 2), 0) AS average_fulfillment_days
            FROM fact_orders
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE VIEW store_performance AS
            SELECT
              store_id,
              COUNT(DISTINCT order_id) AS orders,
              SUM(quantity) AS units,
              SUM(quantity * unit_price) AS revenue,
              SUM(quantity * (unit_price - unit_cost)) AS margin,
              ROUND(AVG(fulfillment_days), 2) AS average_fulfillment_days
            FROM fact_orders
            GROUP BY store_id
            ORDER BY revenue DESC
            """
        )
        connection.execute(
            """
            CREATE OR REPLACE VIEW reorder_queue AS
            -- Grouped per store, not blended across stores: taking
            -- MIN/MAX(inventory_on_hand) across different stores' independent
            -- stock levels produced a "stock_gap" that matched neither
            -- store's actual position for a SKU sold at more than one store.
            -- inventory_on_hand/reorder_level are snapshots recorded on each
            -- order line, so the most recent order per (store, product) is
            -- used as that store's current position.
            WITH latest_snapshot AS (
              SELECT
                store_id, product_id, category, inventory_on_hand, reorder_level,
                ROW_NUMBER() OVER (
                  PARTITION BY store_id, product_id ORDER BY order_date DESC
                ) AS recency_rank
              FROM fact_orders
            ),
            units AS (
              SELECT store_id, product_id, SUM(quantity) AS recent_units
              FROM fact_orders
              GROUP BY store_id, product_id
            )
            SELECT
              s.store_id,
              s.product_id,
              s.category,
              s.inventory_on_hand,
              s.reorder_level,
              u.recent_units,
              s.reorder_level - s.inventory_on_hand AS stock_gap
            FROM latest_snapshot s
            JOIN units u ON u.store_id = s.store_id AND u.product_id = s.product_id
            WHERE s.recency_rank = 1 AND s.inventory_on_hand <= s.reorder_level
            ORDER BY stock_gap DESC, recent_units DESC
            """
        )
        revenue, margin = connection.execute(
            "SELECT COALESCE(SUM(quantity * unit_price), 0), COALESCE(SUM(quantity * (unit_price-unit_cost)), 0) FROM fact_orders"
        ).fetchone()
    finally:
        connection.close()
    return PipelineSummary(len(accepted), len(rejected), Decimal(str(revenue)), Decimal(str(margin)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--database", type=Path, default=Path("retail_ops.duckdb"))
    args = parser.parse_args()
    summary = run(args.input, args.database)
    print(
        f"accepted={summary.accepted} rejected={summary.rejected} "
        f"gross_revenue={summary.gross_revenue:.2f} gross_margin={summary.gross_margin:.2f}"
    )


if __name__ == "__main__":
    main()
