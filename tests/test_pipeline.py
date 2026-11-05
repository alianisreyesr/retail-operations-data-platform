import csv
from decimal import Decimal
from pathlib import Path

import duckdb

from retail_ops.pipeline import run, validate
from retail_ops.report import export_dashboard


def test_validate_explains_invalid_values():
    row = {
        "order_id": "", "order_date": "2026-07-01", "store_id": "ST-01", "product_id": "SKU-1",
        "category": "Home", "quantity": "-1", "inventory_on_hand": "x",
        "reorder_level": "2", "fulfillment_days": "1", "unit_price": "10", "unit_cost": "4",
    }
    assert validate(row) == ["missing_order_id", "negative_quantity", "invalid_inventory_on_hand"]


def test_validate_rejects_malformed_order_date():
    row = {
        "order_id": "ORD-9001", "order_date": "07/01/2026", "store_id": "ST-01", "product_id": "SKU-1",
        "category": "Home", "quantity": "1", "inventory_on_hand": "5",
        "reorder_level": "2", "fulfillment_days": "1", "unit_price": "10", "unit_cost": "4",
    }
    assert validate(row) == ["invalid_order_date"]


def test_bad_order_date_is_rejected_not_a_pipeline_crash(tmp_path: Path):
    source = Path(__file__).parents[1] / "data" / "orders.csv"
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["order_date"] = "not-a-date"
    bad_source = tmp_path / "orders_bad_date.csv"
    with bad_source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    database = tmp_path / "retail.duckdb"
    summary = run(bad_source, database)
    # Only the row with the bad date is rejected; the pipeline must not
    # abort the whole batch (it previously did, via a DuckDB cast error).
    assert summary.rejected == 3
    assert summary.accepted == 7


def test_pipeline_reconciles_and_builds_kpis(tmp_path: Path):
    source = Path(__file__).parents[1] / "data" / "orders.csv"
    database = tmp_path / "retail.duckdb"
    summary = run(source, database)
    assert summary.accepted == 8
    assert summary.rejected == 2
    assert summary.gross_revenue == Decimal("1666.00")
    assert summary.gross_margin == Decimal("698.50")
    connection = duckdb.connect(str(database))
    try:
        assert connection.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0] == 8
        assert connection.execute("SELECT COUNT(*) FROM quality_rejects").fetchone()[0] == 2
        assert connection.execute("SELECT low_stock_lines FROM operations_kpis").fetchone()[0] == 4
    finally:
        connection.close()


def test_decision_views_and_dashboard_are_exportable(tmp_path: Path):
    source = Path(__file__).parents[1] / "data" / "orders.csv"
    database = tmp_path / "retail.duckdb"
    dashboard = tmp_path / "dashboard.html"
    run(source, database)
    payload = export_dashboard(database, dashboard)
    assert payload["metrics"]["orders"] == 8
    assert len(payload["stores"]) == 3
    # reorder_queue is now per (store, product) rather than blended across
    # stores: SKU-101 is below its reorder level independently at both
    # ST-01 and ST-02, so it contributes two rows, not one.
    assert len(payload["reorder_queue"]) == 4
    store_product_pairs = {(row[0], row[1]) for row in payload["reorder_queue"]}
    assert ("ST-01", "SKU-101") in store_product_pairs
    assert ("ST-02", "SKU-101") in store_product_pairs
    assert "Retail Operations Dashboard" in dashboard.read_text()
    assert dashboard.with_suffix(".json").exists()


def test_reorder_queue_does_not_blend_stores(tmp_path: Path):
    """SKU-101 is below reorder level at both ST-01 (9<=10) and ST-02
    (8<=10) with different stock_gap values; each store's true gap must
    be reported separately, not averaged/blended into one row."""
    source = Path(__file__).parents[1] / "data" / "orders.csv"
    database = tmp_path / "retail.duckdb"
    run(source, database)
    connection = duckdb.connect(str(database))
    try:
        rows = connection.execute(
            "SELECT store_id, inventory_on_hand, reorder_level, stock_gap "
            "FROM reorder_queue WHERE product_id = 'SKU-101' ORDER BY store_id"
        ).fetchall()
    finally:
        connection.close()
    assert rows == [
        ("ST-01", 9, 10, 1),
        ("ST-02", 8, 10, 2),
    ]


def test_rerunning_same_file_is_idempotent_not_duplicating(tmp_path: Path):
    source = Path(__file__).parents[1] / "data" / "orders.csv"
    database = tmp_path / "retail.duckdb"
    run(source, database)
    summary_again = run(source, database)
    connection = duckdb.connect(str(database))
    try:
        total = connection.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    finally:
        connection.close()
    assert total == summary_again.accepted == 8


def test_second_batch_accumulates_instead_of_replacing_first(tmp_path: Path):
    """Running a second, different input file must not erase the first
    batch's fact_orders rows — fact_orders is append-by-batch."""
    source = Path(__file__).parents[1] / "data" / "orders.csv"
    database = tmp_path / "retail.duckdb"
    first = run(source, database)

    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["order_id"] = row["order_id"].replace("ORD-1", "ORD-2") if row["order_id"] else row["order_id"]
        row["order_date"] = "2026-07-15"
    second_source = tmp_path / "orders_batch2.csv"
    with second_source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    run(second_source, database)

    connection = duckdb.connect(str(database))
    try:
        total = connection.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    finally:
        connection.close()
    assert total == first.accepted * 2


def test_all_rows_rejected_batch_does_not_crash_kpis(tmp_path: Path):
    bad_source = tmp_path / "orders_all_bad.csv"
    with bad_source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["order_id", "order_date", "store_id", "product_id", "category", "quantity",
             "unit_price", "unit_cost", "inventory_on_hand", "reorder_level", "fulfillment_days"]
        )
        writer.writerow(["ORD-9999", "2026-07-01", "ST-01", "SKU-1", "Home", "-1", "10", "4", "5", "2", "1"])

    database = tmp_path / "retail.duckdb"
    summary = run(bad_source, database)
    assert summary.accepted == 0
    assert summary.rejected == 1
    assert summary.gross_revenue == Decimal("0")
    connection = duckdb.connect(str(database))
    try:
        kpi = connection.execute(
            "SELECT gross_revenue, gross_margin, average_fulfillment_days FROM operations_kpis"
        ).fetchone()
    finally:
        connection.close()
    assert kpi == (0, 0, 0)


def test_zero_rejected_rows_does_not_crash(tmp_path: Path):
    good_source = tmp_path / "orders_all_good.csv"
    with good_source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["order_id", "order_date", "store_id", "product_id", "category", "quantity",
             "unit_price", "unit_cost", "inventory_on_hand", "reorder_level", "fulfillment_days"]
        )
        writer.writerow(["ORD-8001", "2026-07-01", "ST-01", "SKU-1", "Home", "1", "10", "4", "50", "2", "1"])

    database = tmp_path / "retail.duckdb"
    summary = run(good_source, database)
    assert summary.accepted == 1
    assert summary.rejected == 0


HEADER = [
    "order_id", "order_date", "store_id", "product_id", "category", "quantity",
    "unit_price", "unit_cost", "inventory_on_hand", "reorder_level", "fulfillment_days",
]


def _line(order_id="A1", store="ST-01", product="SKU-1", category="Home", qty="2", price="10"):
    return f"{order_id},2026-07-01,{store},{product},{category},{qty},{price},4,50,2,1"


def _write(path: Path, *lines: str) -> Path:
    path.write_text("\n".join([",".join(HEADER), *lines]) + "\n", encoding="utf-8")
    return path


def _query(database: Path, sql: str):
    connection = duckdb.connect(str(database))
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


def _reasons(database: Path) -> list[str]:
    return [r[0] for r in _query(database, "SELECT reasons FROM quality_rejects ORDER BY reasons")]


def test_overlapping_files_do_not_duplicate_orders(tmp_path: Path):
    database = tmp_path / "retail.duckdb"
    first = _write(tmp_path / "a.csv", _line("A1"), _line("A2"))
    second = _write(tmp_path / "b.csv", _line("A1"), _line("A2"), _line("A3"))
    run(first, database)
    summary = run(second, database)
    assert _query(database, "SELECT order_id, COUNT(*) FROM fact_orders GROUP BY 1 ORDER BY 1") == [
        ("A1", 1), ("A2", 1), ("A3", 1),
    ]
    assert summary.gross_revenue == Decimal("60.00")


def test_corrected_resubmission_replaces_the_previous_row(tmp_path: Path):
    database = tmp_path / "retail.duckdb"
    run(_write(tmp_path / "a.csv", _line("A1", qty="2")), database)
    summary = run(_write(tmp_path / "b.csv", _line("A1", qty="5")), database)
    assert summary.gross_revenue == Decimal("50.00")
    assert _query(database, "SELECT COUNT(*) FROM fact_orders") == [(1,)]


def test_duplicate_order_id_within_file_is_rejected(tmp_path: Path):
    database = tmp_path / "retail.duckdb"
    summary = run(_write(tmp_path / "a.csv", _line("A1"), _line("A1", qty="9"), _line("A2")), database)
    assert (summary.accepted, summary.rejected) == (1, 2)
    assert _reasons(database) == ["duplicate_order_id", "duplicate_order_id"]
    assert _query(database, "SELECT order_id FROM fact_orders") == [("A2",)]


def test_empty_business_keys_are_rejected(tmp_path: Path):
    database = tmp_path / "retail.duckdb"
    source = _write(
        tmp_path / "a.csv",
        _line("A1", store=""), _line("A2", product=" "), _line("A3", category=""), _line("A4"),
    )
    summary = run(source, database)
    assert (summary.accepted, summary.rejected) == (1, 3)
    assert _reasons(database) == ["missing_category", "missing_product_id", "missing_store_id"]


def test_truncated_row_is_rejected_not_a_crash(tmp_path: Path):
    database = tmp_path / "retail.duckdb"
    source = _write(tmp_path / "a.csv", _line("A1"), "A2,2026-07-01,ST-01", "")
    summary = run(source, database)
    assert (summary.accepted, summary.rejected) == (1, 1)
    assert "invalid_quantity" in _reasons(database)[0]


def test_validate_handles_none_fields_and_extra_cells():
    row = {"order_id": None, "order_date": None, "unit_price": None, None: ["x"]}
    reasons = validate(row)
    assert "malformed_row" in reasons and "missing_order_id" in reasons
    assert "invalid_order_date" in reasons and "invalid_unit_price" in reasons


def test_run_is_transactional_on_failure(tmp_path: Path, monkeypatch):
    database = tmp_path / "retail.duckdb"
    run(_write(tmp_path / "a.csv", _line("A1")), database)

    import retail_ops.pipeline as pipeline

    real_decimal = pipeline.Decimal

    class Boom(Exception):
        pass

    def exploding(value):
        if value == "77":
            raise Boom()
        return real_decimal(value)

    # Fails inside the insert step, after the reject rows were already written.
    monkeypatch.setattr(pipeline, "Decimal", exploding)
    bad = _write(tmp_path / "b.csv", _line("A2", price="77"), _line("A3", qty="-1"))
    try:
        run(bad, database)
    except Boom:
        pass
    else:
        raise AssertionError("expected failure")
    monkeypatch.undo()
    assert _query(database, "SELECT order_id FROM fact_orders") == [("A1",)]
    assert _query(database, "SELECT COUNT(*) FROM quality_rejects") == [(0,)]
