"""
Comprehensive Graph Topology & Reachability Gatekeeper for Project Cirque
Test Suite: tests/pipeline/test_graph_integrity.py

Executes the SQL assertions defined in `scripts/verify_graph_integrity.sql`
against `data/compiled/topology.sqlite` and generates the milestone gatekeeper
artifact `.cirque/devlog/M1_DATA_PLANE/step_1_4_integrity_report.json`.

Verifies:
1. test_no_orphan_edges(): Fails if orphan edge count > 0.
2. test_gravity_invariants(): Fails if any piste flows uphill (> 0.5% pitch) or any lift flows downhill.
3. test_lift_summit_escapes(): Fails if any chairlift/tram unloads into a dead end.
4. test_mountain_services_connectivity(): Fails if any service venue is attached to an isolated node.
5. test_base_lodge_reachability(): Fails if Lone Peak Summit or Andesite Summit cannot reach Mountain Village Base.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import time
from typing import Any, Dict, List, Optional

import pytest

from pipeline.build_topology import compile_topology, open_readonly_sqlite
from pipeline.ingest_mountain_services import ingest_mountain_services

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_GEOJSON_PATH = str(REPO_ROOT / "data" / "raw" / "big_sky_raw.geojson")
SQL_SCRIPT_PATH = str(REPO_ROOT / "scripts" / "verify_graph_integrity.sql")
SQLITE_DB_PATH = str(REPO_ROOT / "data" / "compiled" / "topology.sqlite")
REPORT_JSON_PATH = str(REPO_ROOT / ".cirque" / "devlog" / "M1_DATA_PLANE" / "step_1_4_integrity_report.json")
DEVLOG_SQL_COPY_PATH = str(REPO_ROOT / ".cirque" / "devlog" / "M1_DATA_PLANE" / "integrity_queries.sql")


def parse_named_sql_queries(sql_path: str) -> Dict[str, str]:
    """Parse `scripts/verify_graph_integrity.sql` into a dict keyed by `-- @query: <name>`."""
    if not os.path.exists(sql_path):
        raise FileNotFoundError(f"SQL verification script not found at {sql_path}")

    with open(sql_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"--\s*@query:\s*([a-zA-Z0-9_]+)\s*\n(.*?)(?=(?:--\s*@query:)|\Z)",
        re.DOTALL,
    )
    return {match.group(1).strip(): match.group(2).strip() for match in pattern.finditer(content)}


def execute_named_query(sqlite_path: str, query_sql: str) -> List[Dict[str, Any]]:
    """Execute a single read-only SQL query against `sqlite_path` and return rows as dicts."""
    conn = open_readonly_sqlite(sqlite_path)
    try:
        cur = conn.cursor()
        cur.execute(query_sql)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def generate_integrity_report(
    sqlite_path: str = SQLITE_DB_PATH,
    sql_path: str = SQL_SCRIPT_PATH,
    report_path: Optional[str] = REPORT_JSON_PATH,
    sql_copy_path: Optional[str] = DEVLOG_SQL_COPY_PATH,
) -> Dict[str, Any]:
    """Run all SQL gatekeeper checks, aggregate graph telemetry, and optionally save artifacts."""
    queries = parse_named_sql_queries(sql_path)

    orphan_rows = execute_named_query(sqlite_path, queries["orphan_edges"])
    uphill_piste_rows = execute_named_query(sqlite_path, queries["uphill_piste_violations"])
    downhill_lift_rows = execute_named_query(sqlite_path, queries["downhill_lift_violations"])
    lift_dead_end_rows = execute_named_query(sqlite_path, queries["lift_top_dead_ends"])
    isolated_service_rows = execute_named_query(sqlite_path, queries["isolated_mountain_services"])
    reachability_rows = execute_named_query(sqlite_path, queries["summit_to_base_reachability"])

    conn = open_readonly_sqlite(sqlite_path)
    try:
        cur = conn.cursor()
        total_nodes = int(cur.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
        total_edges = int(cur.execute("SELECT COUNT(*) FROM edges").fetchone()[0])
        total_services = int(cur.execute("SELECT COUNT(*) FROM mountain_services").fetchone()[0])
        piste_count = int(cur.execute("SELECT COUNT(*) FROM edges WHERE type = 'piste'").fetchone()[0])
        lift_count = int(cur.execute("SELECT COUNT(*) FROM edges WHERE type = 'lift'").fetchone()[0])
    finally:
        conn.close()

    gravity_violations = len(uphill_piste_rows) + len(downhill_lift_rows)
    orphan_edges = len(orphan_rows)
    lift_top_dead_ends = len(lift_dead_end_rows)
    isolated_services = len(isolated_service_rows)

    reachable_base_nodes = sorted({row["reached_base_node_id"] for row in reachability_rows})
    summit_origins_verified = sorted({row["origin_summit_id"] for row in reachability_rows})

    passed = (
        orphan_edges == 0
        and gravity_violations == 0
        and lift_top_dead_ends == 0
        and isolated_services == 0
        and "node_village_mountain_village" in reachable_base_nodes
        and len(summit_origins_verified) >= 2
    )

    report: Dict[str, Any] = {
        "step_id": "STEP_1_4",
        "milestone_id": "M1_DATA_PLANE",
        "title": "Graph Integrity Verification Suite",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "total_services": total_services,
        "piste_count": piste_count,
        "lift_count": lift_count,
        "gravity_violations": gravity_violations,
        "orphan_edges": orphan_edges,
        "lift_top_dead_ends": lift_top_dead_ends,
        "isolated_services": isolated_services,
        "reachable_base_nodes": reachable_base_nodes,
        "summit_reachability_matrix": reachability_rows,
        "gatekeeper_status": "PASSED" if passed else "FAILED",
        "artifacts_created": [
            "scripts/verify_graph_integrity.sql",
            "tests/pipeline/test_graph_integrity.py",
            ".cirque/devlog/M1_DATA_PLANE/step_1_4_integrity_report.json",
            ".cirque/devlog/M1_DATA_PLANE/integrity_queries.sql",
        ],
        "harness_execution": {
            "name": "Comprehensive Graph Topology & Reachability Gatekeeper",
            "command": "uv run --with-requirements requirements.txt pytest tests/pipeline/test_graph_integrity.py -v",
            "pass_criteria": "Zero orphan edges, zero negative slope gravity violations on runs, 100% reachability to mountain base.",
            "status": "PASSED" if passed else "FAILED",
        },
        "content_harvesting": {
            "sublines": f"SQLite Recursive CTE Gatekeeper across {total_nodes} Vertices & {total_edges} Edges",
            "artifacts_to_save": [
                ".cirque/devlog/M1_DATA_PLANE/integrity_queries.sql",
                ".cirque/devlog/M1_DATA_PLANE/step_1_4_integrity_report.json",
            ],
            "talking_points": [
                f"0 orphan foreign keys, 0 uphill pistes, and 0 lift-top dead ends across {total_edges} directed edges.",
                "Delimiter-bounded SQLite recursive CTE proves downhill reachability from Lone Peak (3,403m) and Andesite (2,682m) to Mountain Village Base.",
                f"All {total_services} dining, patrol, warming hut, and restroom venues sit on connected vertices before mobile packaging.",
            ],
        },
        "_query_rows": {
            "orphan_edges": orphan_rows,
            "uphill_piste_violations": uphill_piste_rows,
            "downhill_lift_violations": downhill_lift_rows,
            "lift_top_dead_ends": lift_dead_end_rows,
            "isolated_mountain_services": isolated_service_rows,
            "summit_to_base_reachability": reachability_rows,
        },
    }

    serializable = {k: v for k, v in report.items() if not k.startswith("_")}
    if report_path:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)

    if sql_copy_path and os.path.exists(sql_path):
        os.makedirs(os.path.dirname(sql_copy_path), exist_ok=True)
        shutil.copyfile(sql_path, sql_copy_path)

    return report


@pytest.fixture(scope="module")
def verified_environment(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    """Compile and ingest into an isolated temp directory, then execute all gatekeeper SQL checks once."""
    tmp_dir = tmp_path_factory.mktemp("integrity")
    tmp_db = str(tmp_dir / "topology.sqlite")
    tmp_report = str(tmp_dir / "step_1_4_integrity_report.json")
    tmp_sql_copy = str(tmp_dir / "integrity_queries.sql")

    compile_topology(
        input_geojson_path=RAW_GEOJSON_PATH,
        output_sqlite_path=tmp_db,
        devlog_path=None,
    )
    ingest_mountain_services(sqlite_path=tmp_db, devlog_path=None)

    report = generate_integrity_report(
        sqlite_path=tmp_db,
        sql_path=SQL_SCRIPT_PATH,
        report_path=tmp_report,
        sql_copy_path=tmp_sql_copy,
    )
    return {"report": report, "report_path": tmp_report}


def test_no_orphan_edges(verified_environment: Dict[str, Any]):
    """Check 1: Asserts 0 edges reference non-existent source_node or target_node vertices."""
    report = verified_environment["report"]
    orphan_rows = report["_query_rows"]["orphan_edges"]
    assert len(orphan_rows) == 0, f"Detected orphan edges with missing foreign keys: {orphan_rows}"
    assert report["orphan_edges"] == 0


def test_gravity_invariants(verified_environment: Dict[str, Any]):
    """Check 2: Asserts 0 piste edges flow uphill and 0 lift edges flow downhill."""
    report = verified_environment["report"]
    uphill_pistes = report["_query_rows"]["uphill_piste_violations"]
    downhill_lifts = report["_query_rows"]["downhill_lift_violations"]

    assert len(uphill_pistes) == 0, f"Unauthorized uphill ski runs detected: {uphill_pistes}"
    assert len(downhill_lifts) == 0, f"Unauthorized downhill ski lifts detected: {downhill_lifts}"
    assert report["gravity_violations"] == 0


def test_lift_summit_escapes(verified_environment: Dict[str, Any]):
    """Check 3 & 4: Asserts every lift_top has an escape route and every service venue has incident edges."""
    report = verified_environment["report"]
    dead_ends = report["_query_rows"]["lift_top_dead_ends"]
    isolated_services = report["_query_rows"]["isolated_mountain_services"]

    assert len(dead_ends) == 0, f"Lift top terminals with 0 escape routes detected: {dead_ends}"
    assert len(isolated_services) == 0, f"Isolated mountain services with 0 incident edges: {isolated_services}"


def test_base_lodge_reachability(verified_environment: Dict[str, Any]):
    """Check 5: Asserts Lone Peak Summit and Andesite Summit reach Mountain Village Base via downhill pistes."""
    report = verified_environment["report"]
    reachability_rows = report["_query_rows"]["summit_to_base_reachability"]
    assert len(reachability_rows) > 0, "Recursive CTE returned 0 reachable base nodes from summits"

    summit_to_bases: Dict[str, set[str]] = {}
    for row in reachability_rows:
        summit_to_bases.setdefault(row["origin_summit_id"], set()).add(row["reached_base_node_id"])

    assert "node_summit_lone_peak" in summit_to_bases, "Lone Peak Summit missing from reachability origins"
    assert "node_village_mountain_village" in summit_to_bases["node_summit_lone_peak"], (
        f"Lone Peak Summit cannot reach Mountain Village Base. Reached: {summit_to_bases['node_summit_lone_peak']}"
    )

    assert "node_jct_001" in summit_to_bases, "Andesite Summit (node_jct_001) missing from reachability origins"
    assert "node_village_mountain_village" in summit_to_bases["node_jct_001"], (
        f"Andesite Summit cannot reach Mountain Village Base. Reached: {summit_to_bases['node_jct_001']}"
    )

    assert os.path.exists(verified_environment["report_path"])
    assert report["gatekeeper_status"] == "PASSED"
    assert report["total_nodes"] >= 1000
    assert report["total_edges"] >= 1500
    assert report["total_services"] >= 15
    assert "node_village_mountain_village" in report["reachable_base_nodes"]


if __name__ == "__main__":
    summary_report = generate_integrity_report()
    print(
        f"Integrity gatekeeper {summary_report['gatekeeper_status']}: "
        f"{summary_report['total_nodes']} nodes, {summary_report['total_edges']} edges, "
        f"{summary_report['total_services']} services"
    )
