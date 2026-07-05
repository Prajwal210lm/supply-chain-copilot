"""The reusable generation pipeline: connect, load schema, generate every
table, insert, compute story effects. Both data/generate.py (the CLI entry
point) and tests/test_generator_sanity.py (the determinism check, which
needs to build a second, independent copy under the same seed) call
build_database() directly rather than each re-implementing table order.
"""

from pathlib import Path

import duckdb
import numpy as np

from copilot import constants as C
from copilot.gen import dimensions, effects, supply, transactions


def _insert_df(con, table: str, df, columns: list[str]) -> None:
    con.register("_staging", df[columns])
    col_list = ", ".join(columns)
    con.execute(f"INSERT INTO {table} ({col_list}) SELECT {col_list} FROM _staging")
    con.unregister("_staging")


def build_database(db_path: Path, seed: int = C.SEED, write_stories_json: bool = True) -> dict:
    """Builds a fresh database at db_path (overwriting any existing file)
    and returns {"counts": {...}, "stories_doc": {...}}."""
    rng = np.random.default_rng(seed)

    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))
    con.execute(C.SCHEMA_SQL_PATH.read_text(encoding="utf-8"))

    suppliers_df = dimensions.build_suppliers()
    skus_df = dimensions.build_skus(rng)
    customers_df = dimensions.build_customers(rng)

    _insert_df(con, "suppliers", suppliers_df, ["supplier_id", "supplier_name", "country", "standard_lead_time_days"])
    _insert_df(con, "skus", skus_df, ["sku_id", "sku_name", "category", "abc_class", "unit_cost_aed", "primary_supplier_id"])
    _insert_df(con, "customers", customers_df, ["customer_id", "customer_name", "segment", "emirate"])

    orders_df, lines_df = transactions.build_orders_and_lines(rng, customers_df, skus_df)
    _insert_df(con, "orders", orders_df, ["order_id", "customer_id", "dc", "order_date", "requested_delivery_date", "actual_delivery_date", "order_value_aed"])
    _insert_df(con, "order_lines", lines_df, ["order_id", "sku_id", "qty_ordered", "qty_delivered", "unit_price_aed", "line_value_aed"])

    shipments_df = supply.build_shipments(rng, suppliers_df)
    _insert_df(con, "shipments", shipments_df, ["shipment_id", "supplier_id", "dc", "po_date", "promised_arrival_date", "actual_arrival_date"])

    snapshots_df = supply.build_inventory_snapshots(rng, skus_df, orders_df, lines_df)
    _insert_df(con, "inventory_snapshots", snapshots_df, ["snapshot_month", "sku_id", "dc", "on_hand_qty", "on_hand_value_aed"])

    stories_doc = effects.compute_and_write_stories(con) if write_stories_json else None

    con.close()

    counts = {
        "suppliers": len(suppliers_df), "skus": len(skus_df), "customers": len(customers_df),
        "orders": len(orders_df), "order_lines": len(lines_df),
        "shipments": len(shipments_df), "inventory_snapshots": len(snapshots_df),
    }
    return {"counts": counts, "stories_doc": stories_doc}
