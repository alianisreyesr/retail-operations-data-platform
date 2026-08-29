"""Interactive Streamlit dashboard for the synthetic retail data platform."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

from retail_ops.pipeline import run


ROOT = Path(__file__).parent
DATABASE = ROOT / "retail_ops.duckdb"
SOURCE = ROOT / "data" / "orders.csv"


def ensure_demo_database() -> Path:
    """Build the deterministic demonstration database when it is absent."""
    if not DATABASE.exists():
        run(SOURCE, DATABASE)
    return DATABASE


@st.cache_data
def load_dashboard_data(database_path: str) -> tuple[dict[str, float | int], pd.DataFrame, pd.DataFrame]:
    """Read decision-ready metrics and tables from DuckDB."""
    connection = duckdb.connect(database_path, read_only=True)
    try:
        kpi_row = connection.execute(
            "SELECT order_count, gross_revenue, gross_margin, low_stock_lines, "
            "average_fulfillment_days FROM operations_kpis"
        ).fetchone()
        stores = connection.execute(
            "SELECT store_id, orders, units, revenue, margin, average_fulfillment_days "
            "FROM store_performance ORDER BY revenue DESC"
        ).fetchdf()
        reorder = connection.execute(
            "SELECT store_id, product_id, category, inventory_on_hand, reorder_level, recent_units, stock_gap "
            "FROM reorder_queue ORDER BY stock_gap DESC, recent_units DESC"
        ).fetchdf()
        rejected = connection.execute("SELECT COUNT(*) FROM quality_rejects").fetchone()[0]
    finally:
        connection.close()

    metrics = {
        "orders": int(kpi_row[0]),
        "gross_revenue": float(kpi_row[1]),
        "gross_margin": float(kpi_row[2]),
        "low_stock_lines": int(kpi_row[3]),
        "average_fulfillment_days": float(kpi_row[4]),
        "rejected_records": int(rejected),
    }
    return metrics, stores, reorder


def main() -> None:
    st.set_page_config(page_title="Retail Operations Dashboard", page_icon="📦", layout="centered")
    st.title("Retail Operations Dashboard")
    st.caption("Validated DuckDB metrics generated entirely from fictional portfolio data.")

    metrics, stores, reorder = load_dashboard_data(str(ensure_demo_database()))
    first_row = st.columns(3)
    first_row[0].metric("Orders", metrics["orders"])
    first_row[1].metric("Revenue", f"${metrics['gross_revenue']:,.2f}")
    first_row[2].metric("Margin", f"${metrics['gross_margin']:,.2f}")
    second_row = st.columns(3)
    second_row[0].metric("Low-stock lines", metrics["low_stock_lines"])
    second_row[1].metric("Avg. fulfillment", f"{metrics['average_fulfillment_days']:.2f} days")
    second_row[2].metric("Rejected records", metrics["rejected_records"])

    st.subheader("Revenue and margin by store")
    chart_data = stores.set_index("store_id")[["revenue", "margin"]]
    st.bar_chart(chart_data, color=["#2563EB", "#14B8A6"])
    st.dataframe(
        stores,
        width="stretch",
        hide_index=True,
        column_config={
            "revenue": st.column_config.NumberColumn("Revenue", format="$%.2f"),
            "margin": st.column_config.NumberColumn("Margin", format="$%.2f"),
            "average_fulfillment_days": st.column_config.NumberColumn("Avg. fulfillment", format="%.2f days"),
        },
    )

    st.subheader("Inventory action queue")
    if reorder.empty:
        st.info("No SKUs are currently at or below their reorder level.")
    else:
        category = st.multiselect(
            "Category",
            sorted(reorder["category"].unique()),
            default=sorted(reorder["category"].unique()),
        )
        filtered = reorder[reorder["category"].isin(category)]
        st.dataframe(
            filtered,
            width="stretch",
            hide_index=True,
            column_config={
                "stock_gap": st.column_config.ProgressColumn(
                    "Stock gap",
                    min_value=0,
                    # reorder is non-empty here, so .max() can't be NaN.
                    max_value=max(int(reorder["stock_gap"].max()), 1),
                    format="%d",
                )
            },
        )

    with st.expander("Data quality boundary"):
        st.write(
            "Rows that fail schema or numeric-domain rules are excluded from analytical models and retained "
            "as attributable reject evidence. All bundled records are synthetic."
        )


if __name__ == "__main__":
    main()
