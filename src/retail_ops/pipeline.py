"""Load synthetic retail orders into tested DuckDB analytical models."""

from __future__ import annotations

import argparse
import csv
import hashlib
from dataclasses import dataclass
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
        connection.executemany("INSERT INTO quality_rejects VALUES (?, ?, ?)", [(batch_id, *item) for item in rejected])
        connection.execute("DROP TABLE IF EXISTS fact_orders")
        connection.execute(
            """
            CREATE TABLE fact_orders(
              batch_id VARCHAR, order_id VARCHAR, order_date DATE, store_id VARCHAR,
              product_id VARCHAR, category VARCHAR, quantity INTEGER,
              unit_price DECIMAL(12,2), unit_cost DECIMAL(12,2),
              inventory_on_hand INTEGER, reorder_level INTEGER, fulfillment_days INTEGER
            )
            """
        )
        values = [
            (
                batch_id,
                row["order_id"], row["order_date"], row["store_id"], row["product_id"], row["category"],
                int(row["quantity"]), Decimal(row["unit_price"]), Decimal(row["unit_cost"]),
                int(row["inventory_on_hand"]), int(row["reorder_level"]), int(row["fulfillment_days"]),
            )
            for row in accepted
        ]
        connection.executemany("INSERT INTO fact_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
        connection.execute(
            """
            CREATE OR REPLACE VIEW operations_kpis AS
            SELECT
              COUNT(DISTINCT order_id) AS order_count,
              SUM(quantity * unit_price) AS gross_revenue,
              SUM(quantity * (unit_price - unit_cost)) AS gross_margin,
              COUNT(*) FILTER (WHERE inventory_on_hand <= reorder_level) AS low_stock_lines,
              ROUND(AVG(fulfillment_days), 2) AS average_fulfillment_days
            FROM fact_orders
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
