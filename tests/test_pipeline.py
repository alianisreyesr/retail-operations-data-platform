from decimal import Decimal
from pathlib import Path

import duckdb

from retail_ops.pipeline import run, validate
from retail_ops.report import export_dashboard


def test_validate_explains_invalid_values():
    row = {"order_id": "", "quantity": "-1", "inventory_on_hand": "x", "reorder_level": "2", "fulfillment_days": "1", "unit_price": "10", "unit_cost": "4"}
    assert validate(row) == ["missing_order_id", "negative_quantity", "invalid_inventory_on_hand"]


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
    assert len(payload["reorder_queue"]) == 3
    assert "Retail Operations Dashboard" in dashboard.read_text()
    assert dashboard.with_suffix(".json").exists()
