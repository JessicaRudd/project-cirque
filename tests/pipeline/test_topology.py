"""
Topological Network & Elevation Verification Harness for Project Cirque
Test Suite: tests/pipeline/test_topology.py
Verifies:
1. test_sqlite_schema(): Validates tables, columns, CHECK constraints, and indexes match DDL Section 2.3.
2. test_dag_gravity_polarity(): Asserts 100% of piste edges have vertical_diff_m <= 0 and 100% of lift edges have vertical_diff_m >= 0 across the full 708-piste, 56-lift Big Sky network.
3. test_virtual_transfer_connectivity(): Asserts every one of the 56 lift_top nodes has at least one outgoing edge to a ski trail within 25m.
4. test_summit_to_base_reachability(): Asserts Dijkstra pathfinding resolves a continuous downhill route from Lone Peak Summit to Mountain Village Base.
"""

import os
import sqlite3
import sys
import pytest

# Ensure repo root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pipeline.build_topology import (
    DEM_CACHE_PATH,
    compile_topology,
    find_shortest_downhill_path,
)


@pytest.fixture(scope="module")
def compiled_db_path() -> str:
    """Compile topology.sqlite from data/raw/big_sky_raw.geojson and return database path."""
    input_path = "data/raw/big_sky_raw.geojson"
    output_path = "data/compiled/topology.sqlite"
    summary = compile_topology(input_geojson_path=input_path, output_sqlite_path=output_path)
    assert os.path.exists(output_path), f"Compiled SQLite bundle must exist at {output_path}"
    assert os.path.exists(DEM_CACHE_PATH), f"Live DEM elevation cache must exist at {DEM_CACHE_PATH}"
    assert summary["nodes_total"] >= 1000, f"Expected >= 1000 full-mountain nodes, got {summary['nodes_total']}"
    assert summary["edges_total"] >= 1500, f"Expected >= 1500 full-mountain edges, got {summary['edges_total']}"
    assert summary["lift_edges"] >= 50, f"Expected >= 50 real lift edges, got {summary['lift_edges']}"
    return output_path


def test_sqlite_schema(compiled_db_path: str):
    """
    Validates that all required tables, columns, foreign keys, and indexes exist
    and strictly match the DDL constraints in TECH_SPEC.md Section 2.3.
    """
    conn = sqlite3.connect(compiled_db_path)
    try:
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        expected_tables = {"nodes", "edges", "dynamic_status_overlay", "mountain_services"}
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

        cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cur.fetchall()}
        expected_indexes = {
            "idx_edges_source",
            "idx_edges_target",
            "idx_edges_type_diff",
            "idx_nodes_coords",
            "idx_nodes_poi",
            "idx_services_lookup",
            "idx_services_node",
        }
        assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"

        cur.execute("PRAGMA table_info(nodes)")
        node_cols = {row[1] for row in cur.fetchall()}
        assert node_cols == {
            "node_id",
            "name",
            "lat",
            "lon",
            "elevation_m",
            "node_type",
            "poi_category",
        }

        cur.execute("PRAGMA table_info(edges)")
        edge_cols = {row[1] for row in cur.fetchall()}
        assert edge_cols == {
            "edge_id",
            "source_node",
            "target_node",
            "type",
            "name",
            "difficulty",
            "grooming",
            "length_m",
            "vertical_diff_m",
            "average_pitch_pct",
            "base_cost_seconds",
        }

        with pytest.raises(sqlite3.IntegrityError):
            cur.execute(
                """
                INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category)
                VALUES ('invalid_node_test', 'Bad Node', 45.28, -111.40, 2500.0, 'invalid_type', NULL)
                """
            )
    finally:
        conn.close()


def test_dag_gravity_polarity(compiled_db_path: str):
    """
    Asserts that 100% of piste edges have vertical_diff_m <= 0 (downhill/flat)
    and 100% of lift edges have vertical_diff_m >= 0 (uphill) across the full mountain network.
    """
    conn = sqlite3.connect(compiled_db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT e.edge_id, e.name, e.vertical_diff_m,
                   u.elevation_m AS src_elev, v.elevation_m AS dst_elev
            FROM edges e
            JOIN nodes u ON e.source_node = u.node_id
            JOIN nodes v ON e.target_node = v.node_id
            WHERE e.type = 'piste'
            """
        )
        piste_rows = cur.fetchall()
        assert len(piste_rows) >= 1500, f"Expected >= 1500 piste segments across Big Sky, got {len(piste_rows)}"

        for row in piste_rows:
            assert row["vertical_diff_m"] <= 0.0, (
                f"Piste edge '{row['edge_id']}' ({row['name']}) violates downhill gravity polarity: "
                f"vertical_diff_m={row['vertical_diff_m']} (src={row['src_elev']}m, dst={row['dst_elev']}m)"
            )
            assert row["src_elev"] >= row["dst_elev"], (
                f"Piste edge '{row['edge_id']}' source elevation ({row['src_elev']}m) < target ({row['dst_elev']}m)"
            )

        cur.execute(
            """
            SELECT e.edge_id, e.name, e.vertical_diff_m,
                   u.elevation_m AS src_elev, v.elevation_m AS dst_elev
            FROM edges e
            JOIN nodes u ON e.source_node = u.node_id
            JOIN nodes v ON e.target_node = v.node_id
            WHERE e.type = 'lift'
            """
        )
        lift_rows = cur.fetchall()
        assert len(lift_rows) >= 50, f"Topology must contain all 56 real Big Sky lifts, got {len(lift_rows)}"

        for row in lift_rows:
            assert row["vertical_diff_m"] >= 0.0, (
                f"Lift edge '{row['edge_id']}' ({row['name']}) violates uphill polarity: "
                f"vertical_diff_m={row['vertical_diff_m']}"
            )
            assert row["src_elev"] < row["dst_elev"], (
                f"Lift edge '{row['edge_id']}' must ascend from lower to higher elevation "
                f"(src={row['src_elev']}m, dst={row['dst_elev']}m)"
            )
    finally:
        conn.close()


def test_virtual_transfer_connectivity(compiled_db_path: str):
    """
    Asserts that every `lift_top` node across all 56 lifts has at least one outgoing virtual transfer edge
    to a ski trail (type='piste', difficulty='novice', length_m <= 25.0, base_cost_seconds=30.0).
    """
    conn = sqlite3.connect(compiled_db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        cur.execute("SELECT node_id, name FROM nodes WHERE node_type = 'lift_top'")
        lift_tops = cur.fetchall()
        assert len(lift_tops) >= 50, f"Expected >= 50 lift_top terminal nodes, got {len(lift_tops)}"

        for ltop in lift_tops:
            cur.execute(
                """
                SELECT edge_id, target_node, type, difficulty, length_m, base_cost_seconds
                FROM edges
                WHERE source_node = ? AND type = 'piste'
                """,
                (ltop["node_id"],),
            )
            outgoing_edges = cur.fetchall()
            assert len(outgoing_edges) >= 1, (
                f"Lift top node '{ltop['node_id']}' ({ltop['name']}) has 0 outgoing edges to ski trails"
            )

            for edge in outgoing_edges:
                assert edge["difficulty"] == "novice"
                assert edge["length_m"] <= 25.0, (
                    f"Virtual transfer edge '{edge['edge_id']}' exceeds 25m radius ({edge['length_m']}m)"
                )
                assert edge["base_cost_seconds"] == 30.0
    finally:
        conn.close()


def test_summit_to_base_reachability(compiled_db_path: str):
    """
    Asserts that Dijkstra pathfinding can find a continuous downhill route
    from Lone Peak Summit to Mountain Village Base.
    """
    conn = sqlite3.connect(compiled_db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        cur.execute("SELECT node_id, elevation_m FROM nodes WHERE node_type = 'summit' LIMIT 1")
        summit_row = cur.fetchone()
        assert summit_row is not None, "Lone Peak Summit node (node_type='summit') must exist"
        assert summit_row["elevation_m"] == pytest.approx(3403.0, abs=5.0)

        cur.execute("SELECT node_id, elevation_m FROM nodes WHERE node_type = 'village' LIMIT 1")
        village_row = cur.fetchone()
        assert village_row is not None, "Mountain Village Base node (node_type='village') must exist"
        assert village_row["elevation_m"] == pytest.approx(2286.0, abs=5.0)

        route = find_shortest_downhill_path(
            sqlite_path=compiled_db_path,
            start_node_id=summit_row["node_id"],
            target_node_id=village_row["node_id"],
        )

        assert route is not None, (
            f"Dijkstra failed to find a continuous downhill route from "
            f"{summit_row['node_id']} to {village_row['node_id']}"
        )
        assert len(route["edges"]) >= 3
        assert route["total_vertical_drop_m"] == pytest.approx(2286.0 - 3403.0, abs=10.0)
        assert route["total_cost_seconds"] > 0.0
    finally:
        conn.close()
