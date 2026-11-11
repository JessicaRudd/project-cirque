"""
Topological Network & Elevation Verification Harness for Project Cirque
Test Suite: tests/pipeline/test_topology.py
Verifies:
1. test_sqlite_schema(): Validates tables, columns, CHECK constraints, and indexes match DDL Section 2.3.
2. test_dag_gravity_polarity(): Asserts 100% of piste edges have vertical_diff_m <= 0 and 100% of lift edges have vertical_diff_m >= 0 across the full 708-piste, 56-lift Big Sky network.
3. test_virtual_transfer_connectivity(): Asserts every one of the 56 lift_top nodes has at least one outgoing edge to a ski trail within 25m.
4. test_summit_to_base_reachability(): Asserts Dijkstra pathfinding resolves a continuous downhill route from Lone Peak Summit to Mountain Village Base.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
import pytest

from pipeline.build_topology import (
    DEM_CACHE_PATH,
    compile_topology,
    find_shortest_downhill_path,
    open_readonly_sqlite,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_GEOJSON_PATH = REPO_ROOT / "data" / "raw" / "big_sky_raw.geojson"


@pytest.fixture(scope="module")
def compiled_db_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Compile topology.sqlite into an isolated temp directory for deterministic verification."""
    out_path = tmp_path_factory.mktemp("topology") / "topology.sqlite"
    summary = compile_topology(
        input_geojson_path=str(RAW_GEOJSON_PATH),
        output_sqlite_path=str(out_path),
        devlog_path=None,
    )
    assert out_path.exists(), f"Compiled SQLite bundle must exist at {out_path}"
    assert Path(DEM_CACHE_PATH).exists(), f"DEM elevation cache must exist at {DEM_CACHE_PATH}"
    assert summary["nodes_total"] >= 1000, f"Expected >= 1000 full-mountain nodes, got {summary['nodes_total']}"
    assert summary["edges_total"] >= 1500, f"Expected >= 1500 full-mountain edges, got {summary['edges_total']}"
    assert summary["lift_edges"] >= 50, f"Expected >= 50 lift edges, got {summary['lift_edges']}"
    return str(out_path)


def test_sqlite_schema(compiled_db_path: str):
    """Validates tables, columns, indexes, and nullable CHECK constraints against TECH_SPEC Section 2.3."""
    conn = sqlite3.connect(compiled_db_path)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")

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
                VALUES ('invalid_node_type_test', 'Bad Node', 45.28, -111.40, 2500.0, 'invalid_type', NULL)
                """
            )

        with pytest.raises(sqlite3.IntegrityError):
            cur.execute(
                """
                INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category)
                VALUES ('invalid_poi_cat_test', 'Bad POI Cat', 45.28, -111.40, 2500.0, 'poi', 'quick_snack')
                """
            )

        sample_node = cur.execute("SELECT node_id FROM nodes LIMIT 1").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            cur.execute(
                """
                INSERT INTO edges (
                    edge_id, source_node, target_node, type, name,
                    difficulty, grooming, length_m, vertical_diff_m,
                    average_pitch_pct, base_cost_seconds
                )
                VALUES (?, ?, ?, 'piste', 'Bad Grooming', 'novice', 'slush', 10.0, -1.0, 10.0, 5.0)
                """,
                ("invalid_grooming_edge", sample_node, sample_node),
            )
    finally:
        conn.close()


def test_dag_gravity_polarity(compiled_db_path: str):
    """Asserts 100% of piste edges flow downhill/flat and 100% of lift edges flow uphill."""
    conn = open_readonly_sqlite(compiled_db_path)
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
        assert len(lift_rows) >= 50, f"Expected >= 50 Big Sky lifts, got {len(lift_rows)}"

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
    """Asserts every lift_top node has at least one <= 25m novice unload transfer edge."""
    conn = open_readonly_sqlite(compiled_db_path)
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
    """Asserts Dijkstra resolves a continuous downhill route from Lone Peak Summit to Mountain Village Base."""
    conn = open_readonly_sqlite(compiled_db_path)
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
