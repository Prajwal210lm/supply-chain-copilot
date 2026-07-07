"""Tests for copilot/db.py — written before the module exists (red)."""

import duckdb
import pytest

from copilot import constants as C
from copilot import db


@pytest.fixture(scope="module")
def con():
    connection = db.connect(C.DB_PATH)
    yield connection
    connection.close()


def test_connect_returns_a_working_readonly_connection(con):
    row = con.execute("SELECT COUNT(*) FROM suppliers").fetchone()
    assert row[0] == C.N_SUPPLIERS


def test_insert_through_readonly_connection_raises(con):
    with pytest.raises(duckdb.Error):
        con.execute("INSERT INTO suppliers (supplier_id, supplier_name, country, standard_lead_time_days) VALUES ('X', 'X', 'X', 1)")


def test_update_through_readonly_connection_raises(con):
    with pytest.raises(duckdb.Error):
        con.execute("UPDATE suppliers SET country = 'nowhere' WHERE supplier_id = 'SUP-01'")


def test_delete_through_readonly_connection_raises(con):
    with pytest.raises(duckdb.Error):
        con.execute("DELETE FROM suppliers WHERE supplier_id = 'SUP-01'")


def test_connect_missing_file_raises():
    with pytest.raises(Exception):
        db.connect(C.PROJECT_ROOT / "data" / "does_not_exist.duckdb")
