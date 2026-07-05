-- Mawarid Distribution (fictional) — synthetic data schema.
-- Seven tables, locked shape. Enum-like columns get CHECK constraints so a
-- generator bug (or a future manual edit) fails loudly at insert time rather
-- than silently drifting from the enums pinned in docs/SPEC.md.
--
-- order_lines has no surrogate line_id: (order_id, sku_id) is the natural
-- key because the generator never places the same sku twice on one order.
-- Adding a synthetic id would be schema noise for a key that already exists.

CREATE TABLE suppliers (
    supplier_id              VARCHAR PRIMARY KEY,
    supplier_name            VARCHAR NOT NULL,
    country                  VARCHAR NOT NULL,
    standard_lead_time_days  INTEGER NOT NULL CHECK (standard_lead_time_days > 0)
);

CREATE TABLE skus (
    sku_id               VARCHAR PRIMARY KEY,
    sku_name              VARCHAR NOT NULL,
    category              VARCHAR NOT NULL CHECK (category IN
                           ('food_beverage', 'personal_care', 'home_care', 'otc_pharma', 'baby_care')),
    abc_class             VARCHAR NOT NULL CHECK (abc_class IN ('A', 'B', 'C')),
    unit_cost_aed         DECIMAL(10, 2) NOT NULL CHECK (unit_cost_aed > 0),
    primary_supplier_id   VARCHAR NOT NULL REFERENCES suppliers(supplier_id)
);

CREATE TABLE customers (
    customer_id     VARCHAR PRIMARY KEY,
    customer_name   VARCHAR NOT NULL,
    segment         VARCHAR NOT NULL CHECK (segment IN
                     ('modern_trade', 'traditional_trade', 'pharmacies', 'horeca')),
    emirate         VARCHAR NOT NULL CHECK (emirate IN
                     ('Abu Dhabi', 'Dubai', 'Sharjah', 'Ajman', 'Umm Al Quwain', 'Ras Al Khaimah', 'Fujairah'))
);

CREATE TABLE orders (
    order_id                    VARCHAR PRIMARY KEY,
    customer_id                 VARCHAR NOT NULL REFERENCES customers(customer_id),
    dc                          VARCHAR NOT NULL CHECK (dc IN ('JEB', 'AUH')),
    order_date                  DATE NOT NULL,
    requested_delivery_date     DATE NOT NULL,
    actual_delivery_date        DATE NOT NULL,
    order_value_aed             DECIMAL(12, 2) NOT NULL CHECK (order_value_aed >= 0),
    CHECK (requested_delivery_date >= order_date),
    CHECK (actual_delivery_date >= order_date)
    -- No stored on_time flag: on_time is always derived as
    -- actual_delivery_date <= requested_delivery_date, never persisted, so
    -- there is only one place (query logic) that can get it wrong.
);

CREATE TABLE order_lines (
    order_id          VARCHAR NOT NULL REFERENCES orders(order_id),
    sku_id            VARCHAR NOT NULL REFERENCES skus(sku_id),
    qty_ordered       INTEGER NOT NULL CHECK (qty_ordered > 0),
    qty_delivered     INTEGER NOT NULL CHECK (qty_delivered >= 0),
    unit_price_aed    DECIMAL(10, 2) NOT NULL CHECK (unit_price_aed > 0),
    line_value_aed    DECIMAL(12, 2) NOT NULL CHECK (line_value_aed >= 0),
    PRIMARY KEY (order_id, sku_id),
    CHECK (qty_delivered <= qty_ordered)
);

CREATE TABLE shipments (
    shipment_id              VARCHAR PRIMARY KEY,
    supplier_id              VARCHAR NOT NULL REFERENCES suppliers(supplier_id),
    dc                       VARCHAR NOT NULL CHECK (dc IN ('JEB', 'AUH')),
    po_date                  DATE NOT NULL,
    promised_arrival_date    DATE NOT NULL,
    actual_arrival_date      DATE NOT NULL,
    CHECK (promised_arrival_date >= po_date),
    CHECK (actual_arrival_date >= po_date)
);

CREATE TABLE inventory_snapshots (
    snapshot_month        VARCHAR NOT NULL,   -- ISO month, e.g. "2026-06"
    sku_id                VARCHAR NOT NULL REFERENCES skus(sku_id),
    dc                    VARCHAR NOT NULL CHECK (dc IN ('JEB', 'AUH')),
    on_hand_qty           INTEGER NOT NULL CHECK (on_hand_qty >= 0),
    on_hand_value_aed     DECIMAL(12, 2) NOT NULL CHECK (on_hand_value_aed >= 0),
    PRIMARY KEY (snapshot_month, sku_id, dc)
);
