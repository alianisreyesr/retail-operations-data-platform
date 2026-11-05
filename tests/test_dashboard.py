from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import dashboard
from retail_ops.pipeline import run

ROOT = Path(__file__).parents[1]
HEADER = (
    "order_id,order_date,store_id,product_id,category,quantity,unit_price,unit_cost,"
    "inventory_on_hand,reorder_level,fulfillment_days\n"
)


@pytest.fixture
def database(tmp_path: Path, monkeypatch) -> Path:
    """Point the dashboard at a temp DB so tests never touch a developer's retail_ops.duckdb."""
    path = tmp_path / "retail_ops.duckdb"
    monkeypatch.setattr(dashboard, "DATABASE", path)
    return path


def _render(database: Path, monkeypatch) -> AppTest:
    monkeypatch.setenv("RETAIL_OPS_DATABASE", str(database))
    app = AppTest.from_file(ROOT / "dashboard.py")
    app.run(timeout=30)
    return app


def test_streamlit_dashboard_renders_without_exceptions(tmp_path: Path, monkeypatch):
    database = tmp_path / "db" / "retail_ops.duckdb"  # parent does not exist yet: the app must create it
    app = _render(database, monkeypatch)

    assert not app.exception
    assert app.title[0].value == "Retail Operations Dashboard"
    assert len(app.metric) == 6
    assert database.exists()
    assert len(app.dataframe) == 2
    assert len(app.multiselect) == 1


def test_category_filter_narrows_the_reorder_table(tmp_path: Path, monkeypatch):
    app = _render(tmp_path / "r.duckdb", monkeypatch)
    categories = app.multiselect[0].options
    assert len(categories) >= 2
    app.multiselect[0].set_value([categories[0]]).run(timeout=30)
    assert not app.exception
    shown = app.dataframe[1].value
    assert set(shown["category"]) == {categories[0]}


def test_dashboard_shows_empty_state_without_low_stock(tmp_path: Path, monkeypatch):
    database = tmp_path / "r.duckdb"
    source = tmp_path / "ok.csv"
    source.write_text(HEADER + "A1,2026-07-01,ST-01,SKU-1,Home,1,10,4,50,2,1\n", encoding="utf-8")
    run(source, database)
    app = _render(database, monkeypatch)
    assert not app.exception
    assert [i.value for i in app.info] == ["No SKUs are currently at or below their reorder level."]


def test_ensure_demo_database_builds_once(database: Path):
    assert dashboard.ensure_demo_database() == database
    first = database.stat().st_mtime_ns
    dashboard.ensure_demo_database()
    assert database.stat().st_mtime_ns == first


def test_load_dashboard_data_returns_decimal_money(database: Path):
    from decimal import Decimal

    dashboard.ensure_demo_database()
    dashboard.load_dashboard_data.clear()
    metrics, stores, reorder = dashboard.load_dashboard_data(str(database))
    assert metrics["gross_revenue"] == Decimal("1666.00")
    assert metrics["rejected_records"] == 2
    assert len(stores) == 3 and len(reorder) == 4
