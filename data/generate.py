#!/usr/bin/env python
"""Builds data/mawarid.duckdb from scratch: seeded, deterministic, no
wall-clock dependence anywhere in the call graph below.

Usage: python data/generate.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from copilot import constants as C
from copilot.gen.build import build_database


def main() -> None:
    t0 = time.time()
    print("Generating dimensions, orders, order_lines, shipments, inventory_snapshots...")
    result = build_database(C.DB_PATH)
    elapsed = time.time() - t0

    counts = result["counts"]
    stories_doc = result["stories_doc"]
    size_mb = C.DB_PATH.stat().st_size / (1024 * 1024)

    print("\n" + "=" * 70)
    print("GENERATION SUMMARY")
    print("=" * 70)
    for table, n in counts.items():
        print(f"  {table:22s} {n:>10,d} rows")
    print(f"\n  elapsed: {elapsed:.1f}s")
    print(f"  db file: {C.DB_PATH} ({size_mb:.2f} MB)")

    print("\n  Story effect quick-check:")
    for e in stories_doc["effects"]:
        status = "PASS" if e["pass"] else "FAIL"
        print(f"    [{status}] story {e['story']} {e['metric']} ({e['slice']}): actual={e['actual']!r} expected={e['expected']!r}")

    n_failed = sum(1 for e in stories_doc["effects"] if not e["pass"])
    if n_failed:
        print(f"\n  {n_failed} story effect check(s) FAILED — tune constants.py and regenerate.")
    else:
        print("\n  All story effect checks PASS.")

    if size_mb > C.DB_HARD_STOP_SIZE_MB:
        C.DB_PATH.unlink()
        print(f"\n  REFUSING TO KEEP THE DB FILE: {size_mb:.2f} MB exceeds the "
              f"{C.DB_HARD_STOP_SIZE_MB} MB hard stop. File deleted; reduce scale and regenerate.")
        sys.exit(1)
    elif size_mb > C.DB_WARN_SIZE_MB:
        print(f"\n  WARNING: {size_mb:.2f} MB exceeds the {C.DB_WARN_SIZE_MB} MB target ceiling "
              f"(hard stop is {C.DB_HARD_STOP_SIZE_MB} MB).")

    if n_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
