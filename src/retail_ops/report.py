"""Generate a self-contained recruiter-facing operations dashboard."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import duckdb


def _money(value: float) -> str:
    return f"${value:,.2f}"


def export_dashboard(database_path: Path, output_path: Path) -> dict[str, object]:
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        kpi_row = connection.execute(
            "SELECT order_count, gross_revenue, gross_margin, low_stock_lines, average_fulfillment_days FROM operations_kpis"
        ).fetchone()
        stores = connection.execute(
            "SELECT store_id, orders, units, revenue, margin, average_fulfillment_days FROM store_performance"
        ).fetchall()
        reorder = connection.execute(
            "SELECT product_id, category, inventory_on_hand, reorder_level, recent_units, stock_gap FROM reorder_queue"
        ).fetchall()
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
    store_rows = "".join(
        f"<tr><td>{html.escape(store)}</td><td>{orders}</td><td>{units}</td><td>{_money(float(revenue))}</td><td>{_money(float(margin))}</td><td>{days:.2f} days</td></tr>"
        for store, orders, units, revenue, margin, days in stores
    )
    reorder_rows = "".join(
        f"<tr><td>{html.escape(product)}</td><td>{html.escape(category)}</td><td>{inventory}</td><td>{level}</td><td>{units}</td><td><span class='risk'>Reorder</span></td></tr>"
        for product, category, inventory, level, units, _gap in reorder
    )
    payload = {"metrics": metrics, "stores": [list(row) for row in stores], "reorder_queue": [list(row) for row in reorder]}
    dashboard = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retail Operations Dashboard</title>
<style>
:root{{--ink:#14213d;--muted:#667085;--line:#e5e7eb;--accent:#2563eb;--good:#087f5b;--warn:#b54708;--bg:#f6f8fb}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);font:15px Inter,ui-sans-serif,system-ui;color:var(--ink)}}
main{{max-width:1180px;margin:auto;padding:42px 28px}} .eyebrow{{color:var(--accent);font-weight:800;letter-spacing:.12em;text-transform:uppercase;font-size:12px}}
h1{{font-size:38px;margin:8px 0}} .subtitle{{color:var(--muted);max-width:760px;margin-bottom:28px}} .grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}}
.card,.panel{{background:white;border:1px solid var(--line);border-radius:14px;box-shadow:0 8px 24px #14213d0c}} .card{{padding:18px}}
.label{{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}} .value{{font-size:25px;font-weight:800;margin-top:7px}}
.panels{{display:grid;grid-template-columns:1.2fr 1fr;gap:18px;margin-top:18px}} .panel{{padding:22px}} h2{{font-size:18px;margin:0 0 16px}}
table{{width:100%;border-collapse:collapse}} th{{text-align:left;color:var(--muted);font-size:11px;text-transform:uppercase}} th,td{{padding:11px 8px;border-bottom:1px solid var(--line)}}
.risk{{background:#fff4e5;color:var(--warn);font-weight:700;padding:4px 8px;border-radius:99px}} footer{{color:var(--muted);margin-top:20px;font-size:12px}}
@media(max-width:850px){{.grid{{grid-template-columns:repeat(2,1fr)}}.panels{{grid-template-columns:1fr}}}}
</style></head><body><main>
<div class="eyebrow">Synthetic portfolio evidence</div><h1>Retail Operations Dashboard</h1>
<p class="subtitle">Decision-ready revenue, margin, fulfillment, and inventory signals generated from a validated DuckDB pipeline.</p>
<section class="grid">
<div class="card"><div class="label">Orders</div><div class="value">{metrics['orders']}</div></div>
<div class="card"><div class="label">Revenue</div><div class="value">{_money(metrics['gross_revenue'])}</div></div>
<div class="card"><div class="label">Margin</div><div class="value">{_money(metrics['gross_margin'])}</div></div>
<div class="card"><div class="label">Low-stock lines</div><div class="value">{metrics['low_stock_lines']}</div></div>
<div class="card"><div class="label">Avg fulfillment</div><div class="value">{metrics['average_fulfillment_days']:.2f}d</div></div>
<div class="card"><div class="label">Rejected records</div><div class="value">{metrics['rejected_records']}</div></div>
</section><section class="panels"><article class="panel"><h2>Store performance</h2><table><thead><tr><th>Store</th><th>Orders</th><th>Units</th><th>Revenue</th><th>Margin</th><th>Fulfillment</th></tr></thead><tbody>{store_rows}</tbody></table></article>
<article class="panel"><h2>Inventory action queue</h2><table><thead><tr><th>Product</th><th>Category</th><th>On hand</th><th>Level</th><th>Units</th><th>Action</th></tr></thead><tbody>{reorder_rows}</tbody></table></article></section>
<footer>All records are fictional. This dashboard is generated evidence from a portfolio pipeline, not a production retail system.</footer>
</main></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dashboard, encoding="utf-8")
    output_path.with_suffix(".json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("retail_ops.duckdb"))
    parser.add_argument("--output", type=Path, default=Path("reports/operations-dashboard.html"))
    args = parser.parse_args()
    payload = export_dashboard(args.database, args.output)
    print(f"dashboard={args.output} stores={len(payload['stores'])} reorder_items={len(payload['reorder_queue'])}")


if __name__ == "__main__":
    main()
