"""Every tunable knob for the Mawarid Distribution synthetic data generator.

Nothing in data/generate.py or copilot/gen/*.py should contain a bare numeric
literal that represents a business rule, a rate, a date, or a count — it
should be named here instead. Constants are grouped by concern; each story
section states the target it exists to hit (see docs comments and
data/stories.json, which is emitted by the generator and records the actual
measured effect against these targets).

RNG DISCIPLINE: every generation function receives a single shared
numpy.random.Generator seeded from SEED and consumes it in a fixed call
order (see data/generate.py's main()). Never re-seed mid-run, never use
wall-clock time or os.urandom anywhere in this package — that is what makes
two runs with the same SEED byte-for-byte identical at the query level.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_SQL_PATH = PROJECT_ROOT / "copilot" / "schema.sql"
DB_PATH = PROJECT_ROOT / "data" / "mawarid.duckdb"
STORIES_JSON_PATH = PROJECT_ROOT / "data" / "stories.json"

# Committed-artifact size gate (locked by the build command contract).
DB_WARN_SIZE_MB = 30   # generator prints a warning above this
DB_HARD_STOP_SIZE_MB = 50   # generator refuses to leave the file in place above this

# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------

SEED = 20240701   # arbitrary, fixed forever; never wall-clock. = window start, for memorability only.

# --------------------------------------------------------------------------
# Data window (locked)
# --------------------------------------------------------------------------

WINDOW_START_MONTH = "2024-07"
WINDOW_END_MONTH = "2026-06"
WINDOW_MONTHS = 24          # 2024-07 .. 2026-06 inclusive
NOW_ANCHOR_MONTH = "2026-06"   # matches docs/SPEC.md "now" anchor from step 1

# --------------------------------------------------------------------------
# Scale targets (locked). SCALE_TOLERANCE bands the *sampled* counts
# (orders/lines/shipments) that the sanity tests check row counts against.
# Snapshot rows are NOT sampled — every (sku, dc, month) cell gets exactly
# one row, so that count is exact by construction, not a target to hit.
# --------------------------------------------------------------------------

N_SKUS = 400
N_CUSTOMERS = 60
N_SUPPLIERS = 12
TARGET_ORDER_COUNT = 55_000
TARGET_ORDER_LINE_COUNT = 160_000
TARGET_SHIPMENT_COUNT = 2_900
SCALE_TOLERANCE = 0.10

# ID formatting widths (zero-padded).
SUPPLIER_ID_WIDTH = 2
SKU_ID_WIDTH = 4
CUSTOMER_ID_WIDTH = 2
ORDER_ID_WIDTH = 6
SHIPMENT_ID_WIDTH = 5

# --------------------------------------------------------------------------
# Distribution centers (locked enums)
# --------------------------------------------------------------------------

DC_CODES = ["JEB", "AUH"]   # Jebel Ali (serves Dubai + Northern Emirates), Abu Dhabi

EMIRATES = [
    "Abu Dhabi", "Dubai", "Sharjah", "Ajman",
    "Umm Al Quwain", "Ras Al Khaimah", "Fujairah",
]
# Relative customer-count weighting, roughly population-proportional.
EMIRATE_CUSTOMER_WEIGHT = {
    "Dubai": 35, "Abu Dhabi": 30, "Sharjah": 15, "Ajman": 6,
    "Ras Al Khaimah": 6, "Fujairah": 4, "Umm Al Quwain": 4,
}
# Which DC primarily serves each emirate; drives the order.dc field.
EMIRATE_TO_DC = {
    "Abu Dhabi": "AUH", "Dubai": "JEB", "Sharjah": "JEB", "Ajman": "JEB",
    "Umm Al Quwain": "JEB", "Ras Al Khaimah": "JEB", "Fujairah": "JEB",
}
CROSS_DC_SHIP_RATE = 0.05   # share of orders shipped from the "wrong" dc (routing exceptions)

CATEGORIES = ["food_beverage", "personal_care", "home_care", "otc_pharma", "baby_care"]
CATEGORY_SKU_SHARE = {
    "food_beverage": 0.30, "personal_care": 0.20, "home_care": 0.20,
    "otc_pharma": 0.20, "baby_care": 0.10,
}

ABC_CLASSES = ["A", "B", "C"]
ABC_CLASS_SHARE = {"A": 0.20, "B": 0.30, "C": 0.50}
# Relative draw weight per sku in order-line sampling (Pareto effect: A-class
# SKUs are ordered far more often than their SKU-count share implies).
ABC_LINE_POPULARITY_WEIGHT = {"A": 6.0, "B": 2.0, "C": 1.0}
# A-class lines also tend to be bigger orders (case packs, not onesies).
ABC_QTY_MULTIPLIER = {"A": 1.4, "B": 1.0, "C": 0.7}

SEGMENTS = ["modern_trade", "traditional_trade", "pharmacies", "horeca"]
# 60 customers -> modern_trade 15, traditional_trade 30, pharmacies 9, horeca 6.
# traditional_trade is deliberately sized at 30 to match Story 3's planted
# "~30 customers ordering less frequently" exactly.
SEGMENT_CUSTOMER_SHARE = {
    "modern_trade": 0.25, "traditional_trade": 0.50,
    "pharmacies": 0.15, "horeca": 0.10,
}

# --------------------------------------------------------------------------
# Suppliers (locked reference data — 12 named suppliers, SUP-07 = Anadolu is
# the one locked entity; the rest are fictional but internally consistent).
# --------------------------------------------------------------------------

ANADOLU_SUPPLIER_ID = "SUP-07"
ANADOLU_STANDARD_LEAD_DAYS = 42   # locked

SUPPLIERS_ROSTER = [
    {"supplier_id": "SUP-01", "supplier_name": "Ganges Foods Pvt Ltd", "country": "India", "standard_lead_time_days": 21, "categories": ["food_beverage"]},
    {"supplier_id": "SUP-02", "supplier_name": "Himalaya Baby Care Ltd", "country": "India", "standard_lead_time_days": 24, "categories": ["baby_care"]},
    {"supplier_id": "SUP-03", "supplier_name": "Great Wall Home Products", "country": "China", "standard_lead_time_days": 35, "categories": ["home_care"]},
    {"supplier_id": "SUP-04", "supplier_name": "Pearl River Personal Care Co", "country": "China", "standard_lead_time_days": 33, "categories": ["personal_care"]},
    {"supplier_id": "SUP-05", "supplier_name": "Rheinland Pharma GmbH", "country": "Germany", "standard_lead_time_days": 18, "categories": ["otc_pharma"]},
    {"supplier_id": "SUP-06", "supplier_name": "Nile Delta Beverages", "country": "Egypt", "standard_lead_time_days": 12, "categories": ["food_beverage"]},
    {"supplier_id": ANADOLU_SUPPLIER_ID, "supplier_name": "Anadolu Consumer Goods", "country": "Turkiye", "standard_lead_time_days": ANADOLU_STANDARD_LEAD_DAYS, "categories": ["home_care", "personal_care"]},
    {"supplier_id": "SUP-08", "supplier_name": "Bosphorus Foods A.S.", "country": "Turkiye", "standard_lead_time_days": 20, "categories": ["food_beverage"]},
    {"supplier_id": "SUP-09", "supplier_name": "Najd Home and Personal Care", "country": "Saudi Arabia", "standard_lead_time_days": 8, "categories": ["personal_care", "home_care"]},
    {"supplier_id": "SUP-10", "supplier_name": "Delta Baby Products", "country": "Egypt", "standard_lead_time_days": 14, "categories": ["baby_care"]},
    {"supplier_id": "SUP-11", "supplier_name": "Al Ain Fresh Foods", "country": "United Arab Emirates", "standard_lead_time_days": 3, "categories": ["food_beverage"]},
    {"supplier_id": "SUP-12", "supplier_name": "Emirates Pharma Supply", "country": "United Arab Emirates", "standard_lead_time_days": 4, "categories": ["otc_pharma"]},
]
assert len(SUPPLIERS_ROSTER) == N_SUPPLIERS

# --------------------------------------------------------------------------
# SKU / customer naming flavor (fictional; combined combinatorially with the
# rng so 400 SKUs and 60 customers get varied but deterministic names).
# --------------------------------------------------------------------------

CATEGORY_PRODUCT_NOUNS = {
    "food_beverage": ["Basmati Rice", "Sunflower Oil", "Black Tea", "Instant Coffee", "Tomato Ketchup", "Mixed Nuts", "Long Life Milk", "Orange Juice", "Chocolate Spread", "Biscuits", "Pasta", "Canned Tuna"],
    "personal_care": ["Shampoo", "Body Lotion", "Bar Soap", "Toothpaste", "Deodorant Spray", "Hair Gel", "Shower Gel", "Face Cream", "Hand Wash", "Razor Blades", "Body Spray", "Conditioner"],
    "home_care": ["Dish Liquid", "Laundry Powder", "Surface Cleaner", "Fabric Softener", "Floor Cleaner", "Air Freshener", "Toilet Cleaner", "Glass Cleaner", "Bleach", "Insect Spray", "Dishwasher Tablets", "Furniture Polish"],
    "otc_pharma": ["Paracetamol Tablets", "Cough Syrup", "Antiseptic Cream", "Vitamin C Tablets", "Nasal Spray", "Rehydration Salts", "Pain Relief Gel", "Antacid Tablets", "Multivitamin Syrup", "Throat Lozenges", "Allergy Tablets", "First Aid Spray"],
    "baby_care": ["Baby Diapers", "Baby Wipes", "Baby Shampoo", "Baby Lotion", "Baby Powder", "Baby Formula", "Baby Oil", "Baby Wash", "Diaper Cream", "Baby Cereal", "Baby Sunscreen", "Baby Soap"],
}
SKU_SIZE_VARIANTS = ["250ml", "500ml", "1L", "2L", "100g", "250g", "500g", "1kg", "12-pack", "24-pack", "Travel Size", "Family Pack"]
SKU_BRAND_PREFIXES = ["Wadi", "Falcon", "Desert Rose", "Al Reem", "Barari", "Noor", "Zahra", "Marhaba", "Yasmin", "Sundus", "Qasr", "Waha"]

CUSTOMER_NAME_PREFIXES = [
    "Al Noor", "Al Majid", "Gulf Star", "Desert Palm", "Al Waha", "Emirates Fresh",
    "Al Zahra", "Barka", "Al Rawda", "Gulf Coast", "Al Manar", "Falcon Trading",
    "Al Yasat", "Marina", "Al Bateen", "Sundus", "Al Khaleej", "Union Square",
    "Al Farah", "Palm Grove",
]
SEGMENT_NAME_SUFFIX = {
    "modern_trade": ["Hypermarket", "Supermarket Group", "Retail LLC"],
    "traditional_trade": ["General Trading", "Grocery Store", "Mini Market"],
    "pharmacies": ["Pharmacy", "Pharmacy Group"],
    "horeca": ["Restaurant Group", "Hotel Supplies", "Catering Co"],
}

# --------------------------------------------------------------------------
# Segment behavior: base order frequency, category affinity, dc affinity.
# GLOBAL_ORDER_VOLUME_SCALE is the single knob for hitting TARGET_ORDER_COUNT
# without disturbing the relative segment/category mix.
# --------------------------------------------------------------------------

GLOBAL_ORDER_VOLUME_SCALE = 1.0

SEGMENT_BASE_MONTHLY_ORDERS_PER_CUSTOMER = {
    "modern_trade": 55, "traditional_trade": 30, "pharmacies": 25, "horeca": 35,
}

DEFAULT_CATEGORY_AFFINITY = 1.0
# Multiplier on line-sampling weight per (segment, category). Kept mild on
# purpose: Story 1's cause is upstream of the customer (a supplier delay), so
# every segment must retain real exposure to home_care/personal_care, or the
# "segment cut roughly proportional" target becomes impossible to hit by
# construction rather than by the story's actual (upstream) mechanism.
SEGMENT_CATEGORY_AFFINITY = {
    ("modern_trade", "food_beverage"): 1.1, ("modern_trade", "personal_care"): 1.0,
    ("modern_trade", "home_care"): 1.0, ("modern_trade", "otc_pharma"): 0.7,
    ("modern_trade", "baby_care"): 1.1,
    ("traditional_trade", "food_beverage"): 1.2, ("traditional_trade", "personal_care"): 1.0,
    ("traditional_trade", "home_care"): 1.0, ("traditional_trade", "otc_pharma"): 0.6,
    ("traditional_trade", "baby_care"): 0.9,
    ("pharmacies", "otc_pharma"): 2.2, ("pharmacies", "personal_care"): 1.0,
    ("pharmacies", "baby_care"): 1.1, ("pharmacies", "food_beverage"): 0.3,
    ("pharmacies", "home_care"): 1.0,
    ("horeca", "food_beverage"): 2.0, ("horeca", "home_care"): 1.0,
    ("horeca", "personal_care"): 1.0, ("horeca", "otc_pharma"): 0.2,
    ("horeca", "baby_care"): 0.2,
}
# home_care and personal_care are pinned to EXACTLY 1.0 for every segment
# (unlike the other three categories, which vary by segment for realism) —
# Story 1's cause is upstream of the customer, so segment exposure to the
# two affected categories must not vary by construction, or "roughly
# proportional segment cut" is impossible to hit by the story's own logic.

# --------------------------------------------------------------------------
# Order composition
# --------------------------------------------------------------------------

ORDER_LINE_COUNT_CHOICES = [1, 2, 3, 4, 5]
ORDER_LINE_COUNT_WEIGHTS = [0.14, 0.24, 0.28, 0.22, 0.12]   # mean ~2.9 -> ~160k lines at ~55k orders
ORDER_QTY_MIN = 2
ORDER_QTY_MAX = 40
REQUESTED_LEAD_DAYS_MIN = 1
REQUESTED_LEAD_DAYS_MAX = 4

CATEGORY_UNIT_COST_RANGE_AED = {
    "food_beverage": (3.0, 25.0),
    "personal_care": (8.0, 60.0),
    "home_care": (6.0, 45.0),
    "otc_pharma": (5.0, 80.0),
    "baby_care": (10.0, 70.0),
}
CATEGORY_MARGIN_MULTIPLIER_RANGE = (1.15, 1.45)   # unit_price_aed = unit_cost_aed * multiplier

# --------------------------------------------------------------------------
# Baseline delivery performance (pre-overlay). BASE_ON_TIME_RATE and
# BASE_IN_FULL_RATE combine independently to a baseline OTIF near the top of
# the locked 90-92% band; SEASONALITY_AMPLITUDE pulls some months down into
# the lower half, keeping the swing "small" as required.
# --------------------------------------------------------------------------

BASE_ON_TIME_RATE = 0.965
BASE_IN_FULL_RATE = 0.958
SEASONALITY_AMPLITUDE = 0.007
SEASONALITY_PEAK_MONTH = 12   # calendar month of the seasonal (holiday-volume) dip

LATE_DELAY_DAYS_MIN = 1
LATE_DELAY_DAYS_MAX = 6
SHORT_SHIP_FRACTION_MIN = 0.1   # fraction of qty_ordered withheld on an ordinary short line
SHORT_SHIP_FRACTION_MAX = 0.9
ZERO_DELIVERY_SHARE_OF_SHORT = 0.06   # share of "short" lines that land at qty_delivered = 0

# --------------------------------------------------------------------------
# STORY 1 — March 2026 OTIF drop (Anadolu / SUP-07 shipment delay)
# --------------------------------------------------------------------------

ANADOLU_DELAY_ACTUAL_LEAD_MIN_DAYS = 70
ANADOLU_DELAY_ACTUAL_LEAD_MAX_DAYS = 85
ANADOLU_DELAY_START = "2026-01"   # first po_date month affected by the delay
# Shipments whose PROMISED arrival falls in these months are the ones hit —
# it's their lateness that creates the AUH stock gap.
ANADOLU_DELAY_SHIPMENTS_DUE_MONTHS = ["2026-02", "2026-03"]

STORY1_AFFECTED_DC = "AUH"            # Anadolu volume deliberately concentrated here
STORY1_ANADOLU_AUH_SHIPMENT_SHARE = 0.75   # vs ~0.5 baseline dc split for other suppliers
STORY1_AFFECTED_CATEGORIES = ["home_care", "personal_care"]   # Anadolu's own catalog

# Severity multiplies the peak extra-failure probabilities below, by the
# MONTH THE ORDER WAS PLACED (not the shipment month) — this is what the
# customer actually experiences. Feb carries only a trace bleed since most
# Feb-due shipments land mid/late in the delay; May is essentially recovered,
# matching the ~91% target.
STORY1_MONTH_SEVERITY = {
    "2026-02": 0.05,
    "2026-03": 1.00,
    "2026-04": 0.50,
    "2026-05": 0.10,
}
STORY1_EXTRA_SHORT_PROB_PEAK = 0.80   # extra P(line short-shipped) at severity 1.0, affected lines only
STORY1_EXTRA_LATE_PROB_PEAK = 0.38    # extra P(order late) at severity 1.0, for orders holding an affected line
STORY1_AFFECTED_SHORT_FRACTION_MIN = 0.3
STORY1_AFFECTED_SHORT_FRACTION_MAX = 1.0   # top of range = qty_delivered 0, a true stockout line

# Target bands recorded in stories.json / checked by the sanity suite.
# March band is locked by the brief (83-85%); the rest are "roughly" targets.
STORY1_FEBRUARY_BASELINE_OTIF_BAND = (88.0, 93.0)
STORY1_MARCH_OTIF_BAND = (83.0, 85.0)
STORY1_APRIL_OTIF_BAND = (86.0, 90.0)
STORY1_MAY_OTIF_BAND = (89.5, 93.0)
STORY1_SUP07_LINE_DELTA_SHARE_BAND = (0.50, 0.85)   # SUP-07's share of the Feb->Mar line-grain OTIF delta, "roughly 70%"
STORY1_SEGMENT_CUT_MAX_SPREAD_PP = 11.0   # max spread (pp) across segment OTIF drops, for "roughly proportional"
# horeca has only 6 customers (see SEGMENT_CUSTOMER_SHARE) so its March
# order-grain OTIF sample is small enough that pure sampling noise alone
# produces a few points of spread even with category affinity fully
# flattened for the affected categories (SEGMENT_CATEGORY_AFFINITY) — 8.0
# turned out to reject runs on sampling noise alone, not on a real skew.

# --------------------------------------------------------------------------
# STORY 2 — home_care slow-moving build
# --------------------------------------------------------------------------

SLOWMOVE_CATEGORY = "home_care"
SLOWMOVE_DEMAND_DECLINE_START = "2025-09"
SLOWMOVE_DEMAND_DECLINE_RATE = 0.015   # ~1.5%/month decline in home_care order-line qty, purchasing held flat

# Inventory buildup: on_hand_qty for home_care is set directly from a target
# days_of_cover CURVE (linear ramp, below) multiplied by that sku/dc/month's
# REALIZED trailing-90-day demand (see copilot/gen/supply.py) — not from a
# hardcoded on-hand quantity. This keeps the on-hand side tied to real
# generated transactions (the demand denominator is genuine) while still
# hitting the locked days_of_cover band precisely (the numerator is set to
# make the ratio land exactly on the curve, which is the generator's job:
# it is explicitly planting this effect, not discovering it by accident).
# A pure "purchasing held flat while sales decline 1.5%/month" accumulation
# model was tried first and under-shoots badly: linearizing that dynamic
# over the 9-month Sep-2025..Jun-2026 span only reaches ~85 days, well short
# of the ~105 target — the target ratio needs to be set directly instead of
# emerging from the two independently-locked rates.
SLOWMOVE_DOC_TARGET_START_DAYS = 55.0   # at SLOWMOVE_DEMAND_DECLINE_START, matches the "mid-2025 ~55" anchor
SLOWMOVE_DOC_TARGET_END_DAYS = 105.0    # at WINDOW_END_MONTH

# food_beverage inventory is tightened over the same period (faster turns as
# its sales grow) so TOTAL inventory value stays near flat — the headline
# metric hides the home_care problem by construction, as specified. Modeled
# as a compounding shrink on that category's OWN baseline days_of_cover
# target (same "target-doc x realized demand" construction as home_care).
SLOWMOVE_COUNTER_CATEGORY = "food_beverage"
SLOWMOVE_COUNTER_STOCK_SHRINK_RATE = 0.020
SLOWMOVE_COUNTER_DEMAND_GROWTH_RATE = 0.010   # mild; only the inventory-value and home_care bands are asserted on
# food_beverage also gets a stored-cost multiplier (same decoupling trick as
# home_care's, see STORY2_HOME_CARE_INVENTORY_COST_MULTIPLIER): without it,
# food_beverage's inventory base (~30% SKU share, ordinary unit costs) is
# far too small in absolute AED for any plausible shrink rate to offset
# home_care's multi-million-AED growth. Sized so its absolute AED swing is
# comparable to home_care's, which is what "hides" the problem in the total.
STORY2_FOOD_BEVERAGE_INVENTORY_COST_MULTIPLIER = 10.0

# Target bands recorded in stories.json for the sanity suite (approximate,
# "roughly" per the brief):
SLOWMOVE_DOC_START_BAND_DAYS = (48, 62)     # ~55 days, mid-2025 (2025-07)
SLOWMOVE_DOC_END_BAND_DAYS = (95, 115)      # ~105 days, 2026-06
SLOWMOVE_INVENTORY_VALUE_START_BAND_AED = (8_000_000, 10_000_000)   # ~9M
SLOWMOVE_INVENTORY_VALUE_END_BAND_AED = (13_000_000, 15_000_000)    # ~14M
SLOWMOVE_TOTAL_INVENTORY_FLAT_TOLERANCE = 0.15   # total (all categories) inventory value drift allowed, start vs end
# ("near flat" is judged against home_care's own +~48% category-level swing,
# not against zero — the point is the total moves far less than the part.)

# home_care's stored skus.unit_cost_aed (inventory-valuation basis) is
# inflated by this multiplier relative to the cost basis used to derive
# selling price (see copilot/gen/dimensions.py: build_skus draws a
# reference_cost for pricing, then stores unit_cost_aed = reference_cost for
# every category except home_care, where it stores reference_cost * this
# multiplier). This is a deliberate decoupling, not an oversight: on_hand_qty
# is already pinned by the days_of_cover target curve above, so hitting the
# locked AED 9M/14M bands needs a bigger dollar-per-unit, and doing that via
# unit_cost (inventory-only) rather than unit_price (revenue-facing) means
# the fix cannot leak into Story 3's revenue-flatness check.
STORY2_HOME_CARE_INVENTORY_COST_MULTIPLIER = 6.5

# --------------------------------------------------------------------------
# STORY 3 — traditional_trade quiet churn (demand-side only)
# --------------------------------------------------------------------------

CHURN_SEGMENT = "traditional_trade"
CHURN_COUNTER_SEGMENT = "modern_trade"
CHURN_DECAY_START = "2025-10"
TRAD_TRADE_DECAY_RATE = 0.025      # ~2.5%/month order-count decline per affected customer
MODERN_TRADE_GROWTH_RATE = 0.019   # ~1.5-2%/month order-count growth, offsets revenue

CHURN_DORMANT_CUSTOMER_COUNT = 8    # subset of the 30 traditional_trade customers going fully dormant
CHURN_DORMANT_BY_MONTH = "2026-04"  # "fully dormant by Q2 2026" -> dormant no later than Q2's 2nd month
# Non-dormant decaying customers' order rate never falls below this fraction
# of their own baseline — they slow down, they don't vanish (dormancy is
# reserved for the CHURN_DORMANT_CUSTOMER_COUNT subset).
CHURN_ACTIVE_CUSTOMER_FLOOR_RATE = 0.35

# HARD CONSTRAINT (see copilot/gen/transactions.py where order COUNT is
# decided): Story 3 is demand-side only. It changes how many orders a
# traditional_trade/modern_trade customer places, and NEVER touches
# on_time / short-ship / delivery-outcome logic. The churn calculation is
# fully resolved before any order is generated, and delivery outcomes are
# decided later from a code path that has no knowledge of which story
# produced the order count — so Story 3 cannot leak into Story 1's
# Feb-Mar 2026 AUH/Anadolu decomposition by construction, not by convention.

# --------------------------------------------------------------------------
# Shipments (supplier -> dc replenishment)
# --------------------------------------------------------------------------

SHIPMENT_VOLUME_SCALE = 1.0   # single knob for hitting TARGET_SHIPMENT_COUNT
SHIPMENTS_PER_SUPPLIER_DC_MONTH_MEAN = 5.0
SHIPMENT_LEAD_JITTER_DAYS = 3   # normal supplier noise around standard_lead_time_days, +/- this many days
SHIPMENT_LATE_RATE_BASE = 0.06   # baseline share of shipments arriving a few days late, independent of Story 1
SHIPMENT_LATE_DAYS_MIN = 1
SHIPMENT_LATE_DAYS_MAX = 5
DEFAULT_SUPPLIER_DC_SHARE = 0.5   # baseline JEB/AUH split for suppliers other than Anadolu

# --------------------------------------------------------------------------
# Inventory snapshots
# --------------------------------------------------------------------------

# Baseline days_of_cover per category before any story overlay is applied.
# Used to size the initial on-hand quantity level per sku/dc; from there,
# home_care and food_beverage on-hand quantities evolve via the Story 2
# growth/shrink rates above, and everything else stays flat (with noise).
SNAPSHOT_BASE_DOC_DAYS_BY_CATEGORY = {
    "food_beverage": 35, "personal_care": 50, "home_care": 55,
    "otc_pharma": 60, "baby_care": 45,
}
SNAPSHOT_ONHAND_NOISE = 0.08   # +/- relative noise per sku/dc/month on top of the modeled level
# Nominal on-hand quantity for sku/dc/month cells with zero trailing demand,
# so on_hand_qty is still well-defined without dividing by zero. This never
# feeds a days_of_cover result — a zero-demand cell's days_of_cover is null
# by definition (see fixtures/days_of_cover_fixture.yaml) — it only keeps
# on_hand_qty/value populated for inventory_value queries on that cell.
SNAPSHOT_ZERO_DEMAND_FALLBACK_QTY_BY_ABC = {"A": 20, "B": 10, "C": 4}
