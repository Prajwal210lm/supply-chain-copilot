# QuerySpec Grammar Reference (FROZEN)

This document is the frozen reference for the QuerySpec grammar. Every entry in
`eval/golden_set.yaml` conforms to it. The grammar, enums, and compatibility
matrix below are **locked**; the Resolution Defaults appendix at the end is
policy pinned by the golden set (additive, not part of the locked grammar).

## Envelope

Stage 1 (the model) emits exactly **one JSON object** per turn. The
discriminator field is `spec_type`, with five values:

| spec_type              | Meaning                                              |
|------------------------|------------------------------------------------------|
| `metric_query`         | One metric over one period (optionally as a series)  |
| `breakdown_query`      | One metric split by one dimension over one period    |
| `change_decomposition` | Explain a metric change between two periods          |
| `clarification`        | Question is genuinely undecidable; ask, with options |
| `refusal`              | Cannot or must not answer; typed reason              |

## Period type

```
period: {grain: "month" | "week", start: <ISO>, end: <ISO>}
```

- Inclusive on both ends.
- ISO strings: `"2026-03"` for months, `"2026-W10"` for ISO weeks.
- **Data window: 2024-07 through 2026-06** (inclusive).
- **"Now" anchors to June 2026.** All relative dates ("last month", "YTD",
  "this quarter") resolve against that anchor.
- Quarters and years are not period grains: they **compile to month ranges**
  (Q2 2026 → `{grain: "month", start: "2026-04", end: "2026-06"}`).

## Enums

### metric

```
otif_pct, on_time_pct, in_full_pct, fill_rate_pct, revenue, order_count,
avg_order_value, inventory_value, days_of_cover, stockout_count,
avg_supplier_lead_time
```

`avg_order_value`: revenue divided by order count, based on delivered value, in AED.

### dimension

```
month, week, dc, emirate, category, customer_segment, supplier
```

### reason_code

```
out_of_catalog, incompatible_pair, not_decomposable, out_of_window,
unresolvable_filter, not_a_data_question, unsafe_request
```

## Spec types

### metric_query

```
{spec_type: "metric_query", metric, period, time_grain?, filters?}
```

`time_grain` (`"month"` | `"week"`) requests a series at that grain; omitted
means a single aggregate over the period.

### breakdown_query

```
{spec_type: "breakdown_query", metric, period, dimension, filters?,
 top_n, sort}
```

- `top_n`: integer 1–20, **default 10**.
- `sort`: **default `"desc"`**.

### change_decomposition

```
{spec_type: "change_decomposition", metric, dimension, period_a, period_b,
 filters?}
```

**Both periods are explicit and fully resolved period objects — never
relative.** `period_a` is the baseline, `period_b` the comparison.

### clarification

```
{spec_type: "clarification", question, options, pending_context}
```

- `options`: 2–4 strings, each a plausible concrete reading.
- `pending_context`: partial spec holding everything already resolved
  (filters, period, etc.) so the follow-up turn can complete it.

### refusal

```
{spec_type: "refusal", reason_code, message, suggestions}
```

- `suggestions`: 0–3 strings, each an *answerable* question the user could ask
  instead.

## Filters

```
filters: [{dimension, values: [..]}]
```

- Entity dimensions only: `dc`, `emirate`, `category`, `customer_segment`,
  `supplier`. **Time never appears in filters** — time lives in `period`.
- `values` are the user's **verbatim mention** ("abu dhabi", "anadolu"), not
  canonical IDs. Entity resolution is Stage 2's job.
- Max 3 filters per spec, max 5 values per filter, no duplicate dimensions.

## Compatibility matrix

Applies to breakdown dimensions, decomposition dimensions, and filter
dimensions alike.

| metric                                           | month | week | dc | emirate | category | customer_segment | supplier |
|--------------------------------------------------|:-----:|:----:|:--:|:-------:|:--------:|:----------------:|:--------:|
| otif_pct / on_time_pct / in_full_pct / fill_rate_pct | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| revenue / order_count / avg_order_value          | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| inventory_value / days_of_cover                  | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ |
| stockout_count                                   | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| avg_supplier_lead_time                           | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ |

## Decomposability

Decomposable metrics (valid in `change_decomposition`):

```
otif_pct, on_time_pct, in_full_pct, fill_rate_pct, revenue, order_count,
stockout_count, inventory_value
```

**NOT decomposable** (v2): `avg_order_value`, `days_of_cover`,
`avg_supplier_lead_time`. A "why did X change" question on these is a
`refusal` with `reason_code: not_decomposable`.

## Supplier-cut grain note

**The OTIF family (otif_pct, on_time_pct, in_full_pct) measured by supplier
runs at order-line grain.** An order has one customer but its lines source
from multiple suppliers, so a supplier cut cannot use order-grain counts. A
consequence pinned by `fixtures/decomposition_fixture.yaml`: the order-grain
OTIF delta and the line-grain OTIF delta for the same two months are
legitimately different numbers, and supplier decompositions must reconcile
against the **line-grain** delta.

---

## Appendix: Resolution defaults (pinned by the golden set)

Not part of the locked grammar; these are the default policies the golden
set's clean slice asserts. Changing any of them means re-cutting golden
entries.

1. **Missing period** → latest complete month in the data window:
   `{grain: "month", start: "2026-06", end: "2026-06"}`. Missing periods are
   answered with this default, never clarified.
2. **Trend phrasing without a period** ("trending", "over time") → trailing
   6 months, `time_grain: "month"` (2026-01 through 2026-06).
3. **Relative dates** (anchor = June 2026): last month → 2026-05; this month →
   2026-06; this quarter → 2026-04..2026-06; last quarter → 2026-01..2026-03;
   YTD / this year → 2026-01..2026-06; last year → 2025-01..2025-12; same
   month last year → 2025-06; last N weeks → last N complete ISO weeks ending
   2026-W26 (W27 extends past the window).
4. **Default decomposition dimension** when "why did X change" names none:
   `supplier` for the OTIF family and stockout_count; `category` for revenue,
   order_count, and inventory_value (supplier is incompatible with those).
5. **"Compare A and B" without "why"** → a `metric_query` over the combined
   range with `time_grain` (a trend view), not a decomposition. "Why" is the
   decomposition trigger.
6. **Multi-turn re-emission**: every turn emits a **complete** spec. Follow-ups
   ("break that down by emirate") re-emit the full spec with context merged in
   — never a patch/delta.
