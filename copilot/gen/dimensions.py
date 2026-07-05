"""Reference-data generators: suppliers, skus, customers.

Called once, in this order, from data/generate.py's main(), before any
transactional data — order/shipment/snapshot generation all look up these
tables by id.
"""

import pandas as pd

from copilot import constants as C
from copilot.gen.util import allocate_counts


def build_suppliers() -> pd.DataFrame:
    """Static, locked reference data — no rng draw, no randomness needed."""
    rows = [
        {
            "supplier_id": s["supplier_id"],
            "supplier_name": s["supplier_name"],
            "country": s["country"],
            "standard_lead_time_days": s["standard_lead_time_days"],
        }
        for s in C.SUPPLIERS_ROSTER
    ]
    return pd.DataFrame(rows)


def _eligible_suppliers_by_category() -> dict:
    eligible = {cat: [] for cat in C.CATEGORIES}
    for s in C.SUPPLIERS_ROSTER:
        for cat in s["categories"]:
            eligible[cat].append(s["supplier_id"])
    return eligible


def build_skus(rng) -> pd.DataFrame:
    category_counts = allocate_counts(C.N_SKUS, C.CATEGORY_SKU_SHARE)
    abc_counts = allocate_counts(C.N_SKUS, C.ABC_CLASS_SHARE)

    categories = []
    for cat, n in category_counts.items():
        categories.extend([cat] * n)
    rng.shuffle(categories)

    abc_classes = []
    for cls, n in abc_counts.items():
        abc_classes.extend([cls] * n)
    rng.shuffle(abc_classes)

    eligible_by_category = _eligible_suppliers_by_category()

    rows = []
    for i in range(C.N_SKUS):
        sku_id = f"SKU-{i + 1:0{C.SKU_ID_WIDTH}d}"
        category = categories[i]
        abc_class = abc_classes[i]

        eligible = eligible_by_category[category]
        primary_supplier_id = eligible[int(rng.integers(0, len(eligible)))]

        cost_lo, cost_hi = C.CATEGORY_UNIT_COST_RANGE_AED[category]
        reference_cost_aed = float(rng.uniform(cost_lo, cost_hi))
        margin_lo, margin_hi = C.CATEGORY_MARGIN_MULTIPLIER_RANGE
        base_unit_price_aed = round(reference_cost_aed * float(rng.uniform(margin_lo, margin_hi)), 2)
        # Story 2: home_care's and food_beverage's STORED (inventory-
        # valuation) unit costs are inflated relative to their pricing
        # basis — see STORY2_HOME_CARE_INVENTORY_COST_MULTIPLIER and
        # STORY2_FOOD_BEVERAGE_INVENTORY_COST_MULTIPLIER in constants.py.
        if category == C.SLOWMOVE_CATEGORY:
            unit_cost_aed = round(reference_cost_aed * C.STORY2_HOME_CARE_INVENTORY_COST_MULTIPLIER, 2)
        elif category == C.SLOWMOVE_COUNTER_CATEGORY:
            unit_cost_aed = round(reference_cost_aed * C.STORY2_FOOD_BEVERAGE_INVENTORY_COST_MULTIPLIER, 2)
        else:
            unit_cost_aed = round(reference_cost_aed, 2)

        brand = C.SKU_BRAND_PREFIXES[int(rng.integers(0, len(C.SKU_BRAND_PREFIXES)))]
        noun = C.CATEGORY_PRODUCT_NOUNS[category][int(rng.integers(0, len(C.CATEGORY_PRODUCT_NOUNS[category])))]
        size = C.SKU_SIZE_VARIANTS[int(rng.integers(0, len(C.SKU_SIZE_VARIANTS)))]
        sku_name = f"{brand} {noun} {size}"

        rows.append({
            "sku_id": sku_id,
            "sku_name": sku_name,
            "category": category,
            "abc_class": abc_class,
            "unit_cost_aed": unit_cost_aed,
            "primary_supplier_id": primary_supplier_id,
            # in-memory only, used by transactions.py; not a schema column.
            "base_unit_price_aed": base_unit_price_aed,
        })
    return pd.DataFrame(rows)


def build_customers(rng) -> pd.DataFrame:
    segment_counts = allocate_counts(C.N_CUSTOMERS, C.SEGMENT_CUSTOMER_SHARE)
    emirate_counts = allocate_counts(C.N_CUSTOMERS, C.EMIRATE_CUSTOMER_WEIGHT)

    segments = []
    for seg, n in segment_counts.items():
        segments.extend([seg] * n)
    rng.shuffle(segments)

    emirates = []
    for em, n in emirate_counts.items():
        emirates.extend([em] * n)
    rng.shuffle(emirates)

    used_names = set()
    rows = []
    for i in range(C.N_CUSTOMERS):
        customer_id = f"CUST-{i + 1:0{C.CUSTOMER_ID_WIDTH}d}"
        segment = segments[i]
        emirate = emirates[i]

        prefix = C.CUSTOMER_NAME_PREFIXES[int(rng.integers(0, len(C.CUSTOMER_NAME_PREFIXES)))]
        suffix_options = C.SEGMENT_NAME_SUFFIX[segment]
        suffix = suffix_options[int(rng.integers(0, len(suffix_options)))]
        name = f"{prefix} {suffix}"
        disambiguator = 2
        base_name = name
        while name in used_names:
            name = f"{base_name} {disambiguator}"
            disambiguator += 1
        used_names.add(name)

        rows.append({
            "customer_id": customer_id,
            "customer_name": name,
            "segment": segment,
            "emirate": emirate,
        })
    return pd.DataFrame(rows)
