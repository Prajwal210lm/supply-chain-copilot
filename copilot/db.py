"""Read-only connection management. One helper, one job: the compiler must
never be able to write to data/mawarid.duckdb — DuckDB's own read_only mode
is the enforcement, not application-level discipline.
"""

from pathlib import Path

import duckdb


def connect(path: str | Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(path), read_only=True)
