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

from __future__ import annotations

from pathlib import Path
import re
import sqlite3
import pytest

from pipeline.build_topology import compile_topology, open_readonly_sqlite
from pipeline.ingest_mountain_services import ingest_mountain_services

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_GEOJSON_PATH = REPO_ROOT / "data" / "raw" / "big_sky_raw.geojson"


@pytest.fixture(scope="module")
def services_db_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Compile topology.sqlite in a temp dir and verify idempotent mountain_services ingestion."""
    sqlite_path = tmp_path_factory.mktemp("services") / "topology.sqlite"
    compile_topology(
        input_geojson_path=str(RAW_GEOJSON_PATH),
        output_sqlite_path=str(sqlite_path),
        devlog_path=None,
    )
    first_run = ingest_mountain_services(sqlite_path=str(sqlite_path), devlog_path=None)
    second_run = ingest_mountain_services(sqlite_path=str(sqlite_path), devlog_path=None)
    assert first_run["metrics"]["total_services"] == second_run["metrics"]["total_services"] == 15
    assert first_run["metrics"]["virtual_walk_edges_injected"] == second_run["metrics"]["virtual_walk_edges_injected"]
    return str(sqlite_path)


def test_mountain_services_table_populated(services_db_path: str):
    """Asserts mountain_services populates all 7 required categories and enforces service_speed CHECK constraints."""
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
            "restroom",
        }
        missing = required_categories - present_categories
        assert not missing, f"Missing required amenity categories: {missing}"

        cur.execute("SELECT name FROM mountain_services")
        venue_names = {row[0] for row in cur.fetchall()}
        assert {"Shedhorn Grill", "Everett's 8800", "Vista Hall", "Montana Jack"}.issubset(venue_names)

        sample_node = cur.execute("SELECT node_id FROM mountain_services LIMIT 1").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            cur.execute(
                """
                INSERT INTO mountain_services (
                    service_id, node_id, name, category, service_speed,
                    open_time_local, close_time_local, requires_reservation,
                    price_tier, is_ski_in_only, daily_status
                )
                VALUES (?, ?, 'Bad Speed', 'quick_snack', 'drive_thru', '09:00', '16:00', 0, '$', 0, 'open')
                """,
                ("invalid_speed_srv", sample_node),
            )
    finally:
        conn.close()


def test_node_foreign_key_integrity(services_db_path: str):
    """Asserts 100% of mountain_services node_ids resolve to valid nodes with zero FK violations."""
    conn = open_readonly_sqlite(services_db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.service_id, s.name AS service_name, s.node_id, n.node_id AS matched_node_id
            FROM mountain_services s
            LEFT JOIN nodes n ON s.node_id = n.node_id
            """
        )
        rows = cur.fetchall()
        assert len(rows) == 15

        for row in rows:
            assert row["matched_node_id"] == row["node_id"], (
                f"Service '{row['service_name']}' ({row['service_id']}) references missing node_id '{row['node_id']}'"
            )

        cur.execute("PRAGMA foreign_key_check(mountain_services)")
        fk_violations = cur.fetchall()
        assert len(fk_violations) == 0, f"Foreign key violations detected: {fk_violations}"
    finally:
        conn.close()


def test_operating_hours_format(services_db_path: str):
    """Asserts all open_time_local and close_time_local follow 24-hour HH:MM format with open < close."""
    time_regex = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

    conn = open_readonly_sqlite(services_db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT service_id, name, open_time_local, close_time_local FROM mountain_services")
        for row in cur.fetchall():
            open_str = row["open_time_local"]
            close_str = row["close_time_local"]
            assert time_regex.match(open_str), f"Invalid open_time_local '{open_str}' on '{row['name']}'"
            assert time_regex.match(close_str), f"Invalid close_time_local '{close_str}' on '{row['name']}'"

            open_h, open_m = map(int, open_str.split(":"))
            close_h, close_m = map(int, close_str.split(":"))
            assert (open_h * 60 + open_m) < (close_h * 60 + close_m), (
                f"Service '{row['name']}' has close_time ({close_str}) <= open_time ({open_str})"
            )
    finally:
        conn.close()


def test_quick_snack_query(services_db_path: str):
    """Verifies resolveTargetNodes SQL query returns Shedhorn Grill open at 13:15 on a connected vertex."""
    query_time = "13:15"
    conn = open_readonly_sqlite(services_db_path)
    try:
        cur = conn.cursor()
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
            ("quick_snack", "grab_and_go", query_time),
        )
        results = [dict(r) for r in cur.fetchall()]
        assert len(results) > 0

        shedhorn = next((v for v in results if "Shedhorn Grill" in v["name"]), None)
        assert shedhorn is not None, f"Shedhorn Grill should be open at {query_time}"
        assert shedhorn["is_ski_in_only"] == 1
        assert shedhorn["open_time_local"] <= query_time <= shedhorn["close_time_local"]

        cur.execute(
            "SELECT COUNT(*) FROM edges WHERE source_node = ? OR target_node = ?",
            (shedhorn["node_id"], shedhorn["node_id"]),
        )
        assert cur.fetchone()[0] > 0, f"Node {shedhorn['node_id']} must have connected graph edges"
    finally:
        conn.close()
