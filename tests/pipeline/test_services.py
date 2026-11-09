"""
Amenity Junction Snapping & Operating Hours Harness for Project Cirque
Test Suite: tests/pipeline/test_services.py

Verifies:
1. test_mountain_services_table_populated():
   Asserts that `mountain_services` contains all required categories:
   'quick_snack', 'cafeteria', 'sit_down', 'bar', 'patrol', and 'warming_hut'.
2. test_node_foreign_key_integrity():
   Asserts that 100% of `node_id`s in `mountain_services` exist in the `nodes` table.
3. test_operating_hours_format():
   Asserts all `open_time_local` and `close_time_local` adhere to 'HH:MM' 24-hour format
   and open_time < close_time.
4. test_quick_snack_query():
   Executes a test query filtering for open grab-and-go venues at '13:15',
   asserting that Shedhorn Grill is returned with a valid, connected graph node.
"""

import os
import re
import sqlite3
import sys
from typing import Any, Dict, List
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pipeline.ingest_mountain_services import ingest_mountain_services


@pytest.fixture(scope="module")
def services_db_path() -> str:
    """Ensure topology.sqlite exists and mountain_services is freshly ingested."""
    sqlite_path = "data/compiled/topology.sqlite"
    devlog_path = ".cirque/devlog/M1_DATA_PLANE/step_1_3.json"
    assert os.path.exists(sqlite_path), f"Base database {sqlite_path} must exist before running tests"
    telemetry = ingest_mountain_services(sqlite_path=sqlite_path, devlog_path=devlog_path)
    assert telemetry["metrics"]["total_services"] > 0
    return sqlite_path


def test_mountain_services_table_populated(services_db_path: str):
    """
    Asserts that `mountain_services` contains all required categories:
    quick_snack, cafeteria, sit_down, bar, patrol, and warming_hut.
    """
    conn = sqlite3.connect(services_db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM mountain_services")
        present_categories = {row[0] for row in cur.fetchall()}

        required_categories = {
            "quick_snack",
            "cafeteria",
            "sit_down",
            "bar",
            "patrol",
            "warming_hut",
        }
        missing = required_categories - present_categories
        assert not missing, f"Missing required amenity categories: {missing}"

        # Verify key venues exist by name
        cur.execute("SELECT name FROM mountain_services")
        venue_names = {row[0] for row in cur.fetchall()}
        assert "Shedhorn Grill" in venue_names
        assert "Everett's 8800" in venue_names
        assert "Vista Hall" in venue_names
        assert "Montana Jack" in venue_names
    finally:
        conn.close()


def test_node_foreign_key_integrity(services_db_path: str):
    """
    Asserts that 100% of node_ids in `mountain_services` exist in the `nodes` table.
    Ensures referential integrity for graph routing and Dijkstra solvers.
    """
    conn = sqlite3.connect(services_db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        # Query all services with their referenced nodes
        cur.execute(
            """
            SELECT s.service_id, s.name AS service_name, s.node_id, n.node_id AS matched_node_id,
                   n.name AS node_name, n.lat, n.lon
            FROM mountain_services s
            LEFT JOIN nodes n ON s.node_id = n.node_id
            """
        )
        rows = cur.fetchall()
        assert len(rows) > 0, "mountain_services table must have rows"

        for row in rows:
            assert row["matched_node_id"] is not None, (
                f"Service '{row['service_name']}' ({row['service_id']}) references "
                f"non-existent node_id: '{row['node_id']}'"
            )
            assert row["node_id"] == row["matched_node_id"]

        # Run SQLite's built-in foreign key integrity check
        cur.execute("PRAGMA foreign_key_check(mountain_services)")
        fk_violations = cur.fetchall()
        assert len(fk_violations) == 0, f"Foreign key violations detected: {fk_violations}"
    finally:
        conn.close()


def test_operating_hours_format(services_db_path: str):
    """
    Asserts that all open_time_local and close_time_local adhere to 'HH:MM' 24-hour format
    and open_time < close_time.
    """
    time_regex = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

    conn = sqlite3.connect(services_db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT service_id, name, open_time_local, close_time_local FROM mountain_services")
        rows = cur.fetchall()

        for row in rows:
            open_str = row["open_time_local"]
            close_str = row["close_time_local"]

            assert time_regex.match(open_str), (
                f"Service '{row['name']}' has invalid open_time_local: '{open_str}'. Expected 'HH:MM'."
            )
            assert time_regex.match(close_str), (
                f"Service '{row['name']}' has invalid close_time_local: '{close_str}'. Expected 'HH:MM'."
            )

            # Convert to minutes past midnight
            open_h, open_m = map(int, open_str.split(":"))
            close_h, close_m = map(int, close_str.split(":"))
            open_mins = open_h * 60 + open_m
            close_mins = close_h * 60 + close_m

            assert open_mins < close_mins, (
                f"Service '{row['name']}' has close_time ({close_str}) <= open_time ({open_str})"
            )
    finally:
        conn.close()


def test_quick_snack_query(services_db_path: str):
    """
    Simulates on-device intent routing:
    Executes a test query filtering for open grab-and-go venues at '13:15',
    asserting that Shedhorn Grill is returned with a valid snapped graph node.
    """
    query_time = "13:15"
    target_category = "quick_snack"
    target_speed = "grab_and_go"

    conn = sqlite3.connect(services_db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        # Query adhering to TECH_SPEC.md Section 4 (resolveTargetNodes)
        cur.execute(
            """
            SELECT s.service_id, s.name, s.category, s.service_speed,
                   s.open_time_local, s.close_time_local, s.is_ski_in_only,
                   s.node_id, n.lat, n.lon, n.elevation_m
            FROM mountain_services s
            JOIN nodes n ON s.node_id = n.node_id
            WHERE s.category = ?
              AND s.service_speed = ?
              AND ? BETWEEN s.open_time_local AND s.close_time_local
              AND s.daily_status = 'open'
            """,
            (target_category, target_speed, query_time),
        )
        results = [dict(r) for r in cur.fetchall()]
        assert len(results) > 0, f"Expected at least one open quick snack venue at {query_time}"

        # Assert Shedhorn Grill is among the returned venues
        shedhorn = next((v for v in results if "Shedhorn Grill" in v["name"]), None)
        assert shedhorn is not None, f"Shedhorn Grill should be open at {query_time}"
        assert shedhorn["is_ski_in_only"] == 1
        assert shedhorn["open_time_local"] <= query_time <= shedhorn["close_time_local"]
        assert shedhorn["node_id"] is not None

        # Verify the assigned node has navigable edges connected in `edges`
        cur.execute(
            """
            SELECT COUNT(*) FROM edges
            WHERE source_node = ? OR target_node = ?
            """,
            (shedhorn["node_id"], shedhorn["node_id"]),
        )
        connected_edges = cur.fetchone()[0]
        assert connected_edges > 0, f"Node {shedhorn['node_id']} must have connected graph edges"
    finally:
        conn.close()
