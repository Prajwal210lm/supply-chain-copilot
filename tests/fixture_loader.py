"""Adapts the three pinned fixtures (fixtures/*.yaml) into rows matching
copilot/schema.sql, loaded into a throwaway in-memory DuckDB for
test_integration_fixture.py.

This file is test support code, not a test module itself, and it NEVER
writes to fixtures/ or eval/ — it only reads them. The fixtures describe
their data at a conceptual level (an order's on_time flag and its lines;
a supplier code; a sku code) rather than as literal schema rows (no
customer_id, no explicit dates, no per-line sku_id in some cases) — the
synthesis choices below (customer/sku ids, mid-month order dates, request
lead + late-delay days) are this loader's own, chosen because none of them
are asserted on by any fixture; only the values the fixtures DO pin
(on_time, in_full, quantities, prices, snapshot quantities/values) flow
through unchanged.

GATE: every fixture must be hand_verified: true, or this refuses to load —
see the shared comment block at the top of each fixtures/*.yaml file.
"""

from datetime import date, timedelta
from pathlib import Path

import duckdb
import yaml

from copilot import constants as C

FIXTURES_DIR = C.PROJECT_ROOT / "fixtures"

_GENERIC_CUSTOMER_ID = "FIX-CUST-1"
_GENERIC_SUPPLIER_ID = "SUP-X"


class FixtureNotVerifiedError(Exception):
    pass


def _load_yaml(name: str) -> dict:
    path = FIXTURES_DIR / name
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if doc.get("hand_verified") is not True:
        raise FixtureNotVerifiedError(
            name + " has hand_verified=" + repr(doc.get("hand_verified")) + "; refusing to treat it as pinned."
        )
    return doc


def _month_mid_date(month: str) -> date:
    year, mon = int(month[:4]), int(month[5:7])
    return date(year, mon, 15)


def _build_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(C.SCHEMA_SQL_PATH.read_text(encoding="utf-8"))
    con.execute(
        "INSERT INTO suppliers VALUES ('S1','Fixture Supplier One','Testland',30)"
    )
    con.execute(
        "INSERT INTO suppliers VALUES ('S2','Fixture Supplier Two','Testland',30)"
    )
    con.execute(
        "INSERT INTO suppliers VALUES ('" + _GENERIC_SUPPLIER_ID + "','Fixture Generic Supplier','Testland',30)"
    )
    con.execute(
        "INSERT INTO customers VALUES ('" + _GENERIC_CUSTOMER_ID + "','Fixture Customer','modern_trade','Dubai')"
    )


def _insert_order(con, order_id: str, order_date: date, on_time: bool, dc: str, lines: list) -> None:
    """lines: list of dicts with qty_ordered/qty_delivered/unit_price_aed,
    and OPTIONALLY an explicit sku_id (must already exist in skus) — if
    omitted, falls back to the "FIX-SKU-<order_id>-L<i>" naming the
    decomposition/overlap loaders pre-create rows under."""
    requested = order_date + timedelta(days=3)
    actual = requested if on_time else requested + timedelta(days=5)
    order_value = round(sum(l["qty_ordered"] * l["unit_price_aed"] for l in lines), 2)
    con.execute(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)",
        [order_id, _GENERIC_CUSTOMER_ID, dc, order_date, requested, actual, order_value],
    )
    for i, line in enumerate(lines):
        sku_id = line.get("sku_id") or ("FIX-SKU-" + order_id + "-L" + str(i))
        line_value = round(line["qty_delivered"] * line["unit_price_aed"], 2)
        con.execute(
            "INSERT INTO order_lines VALUES (?, ?, ?, ?, ?, ?)",
            [order_id, sku_id, line["qty_ordered"], line["qty_delivered"], line["unit_price_aed"], line_value],
        )


def _load_decomposition_fixture(con, doc: dict) -> None:
    skus_inserted = set()
    for order in doc["orders"]:
        supplier_id = order["supplier"]
        for i in range(len(order["lines"])):
            sku_id = "FIX-SKU-" + order["order_id"] + "-L" + str(i)
            if sku_id not in skus_inserted:
                con.execute(
                    "INSERT INTO skus VALUES (?, ?, 'food_beverage', 'A', 1.00, ?)",
                    [sku_id, sku_id, supplier_id],
                )
                skus_inserted.add(sku_id)
        order_date = _month_mid_date(order["month"])
        _insert_order(con, order["order_id"], order_date, order["on_time"], order["dc"], order["lines"])


def _load_otif_overlap_fixture(con, doc: dict) -> None:
    # Fixture has no month/dc — these orders exist only to pin the OTIF
    # union rule, not any period- or dc-cut behavior, so both are fixed
    # arbitrary constants. 2026-01 is deliberately clear of the other two
    # fixtures' months: decomposition uses 2026-02/03, and days_of_cover's
    # synthetic demand orders span 2026-04/05/06 — sharing a month with
    # either would contaminate this fixture's period-scoped queries.
    order_date = date(2026, 1, 10)
    for order in doc["orders"]:
        for i in range(len(order["lines"])):
            sku_id = "FIX-SKU-" + order["order_id"] + "-L" + str(i)
            con.execute(
                "INSERT INTO skus VALUES (?, ?, 'food_beverage', 'A', 1.00, ?)",
                [sku_id, sku_id, _GENERIC_SUPPLIER_ID],
            )
        _insert_order(con, order["order_id"], order_date, order["on_time"], "JEB", order["lines"])


def _load_days_of_cover_fixture(con, doc: dict) -> None:
    for row in doc["snapshots"]:
        con.execute(
            "INSERT INTO skus VALUES (?, ?, 'home_care', 'A', 1.00, ?) "
            "ON CONFLICT (sku_id) DO NOTHING",
            [row["sku"], row["sku"], _GENERIC_SUPPLIER_ID],
        )
    for row in doc["snapshots"]:
        con.execute(
            "INSERT INTO inventory_snapshots VALUES (?, ?, ?, ?, ?)",
            [row["month"], row["sku"], row["dc"], row["on_hand_qty"], row["on_hand_value_aed"]],
        )

    # Synthesize orders/order_lines so trailing-90-day demand computed from
    # REAL order_lines rows reproduces the fixture's pinned demand_2026_0X
    # figures exactly. One order per non-zero (sku, dc, month) demand cell.
    month_cols = {"2026-04": "demand_2026_04", "2026-05": "demand_2026_05", "2026-06": "demand_2026_06"}
    seq = 0
    for row in doc["trailing_90d_demand"]:
        for month, col in month_cols.items():
            qty = row[col]
            if qty <= 0:
                continue
            seq += 1
            order_id = "FIX-DOC-ORD-" + str(seq)
            order_date = _month_mid_date(month)
            _insert_order(
                con, order_id, order_date, True, row["dc"],
                [{"sku_id": row["sku"], "qty_ordered": qty, "qty_delivered": qty, "unit_price_aed": 1.00}],
            )


def load_all_fixtures() -> dict:
    """Returns {"con": duckdb connection, "decomposition": doc, "overlap": doc, "days_of_cover": doc}."""
    decomposition_doc = _load_yaml("decomposition_fixture.yaml")
    overlap_doc = _load_yaml("otif_overlap_fixture.yaml")
    doc_doc = _load_yaml("days_of_cover_fixture.yaml")

    con = duckdb.connect(":memory:")
    _build_schema(con)
    _load_decomposition_fixture(con, decomposition_doc)
    _load_otif_overlap_fixture(con, overlap_doc)
    _load_days_of_cover_fixture(con, doc_doc)

    return {
        "con": con,
        "decomposition": decomposition_doc,
        "overlap": overlap_doc,
        "days_of_cover": doc_doc,
    }
