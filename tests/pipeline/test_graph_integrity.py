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
import re
import shutil
import sqlite3
import sys
import time
from typing import Any, Dict, List

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pipeline.build_topology import compile_topology
from pipeline.ingest_mountain_services import ingest_mountain_services

SQL_SCRIPT_PATH = "scripts/verify_graph_integrity.sql"
SQLITE_DB_PATH = "data/compiled/topology.sqlite"
REPORT_JSON_PATH = ".cirque/devlog/M1_DATA_PLANE/step_1_4_integrity_report.json"
DEVLOG_SQL_COPY_PATH = ".cirque/devlog/M1_DATA_PLANE/integrity_queries.sql"


def parse_named_sql_queries(sql_path: str) -> Dict[str, str]:
    """
    Parse `scripts/verify_graph_integrity.sql` into a dictionary of named SQL queries
    keyed by `-- @query: <name>` annotations.
    """
    if not os.path.exists(sql_path):
        raise FileNotFoundError(f"SQL verification script not found at {sql_path}")

    with open(sql_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"--\s*@query:\s*([a-zA-Z0-9_]+)\s*\n(.*?)(?=(?:--\s*@query:)|\Z)",
        re.DOTALL,
    )
    queries: Dict[str, str] = {}
    for match in pattern.finditer(content):
        q_name = match.group(1).strip()
        q_body = match.group(2).strip()
        queries[q_name] = q_body

    return queries


def execute_named_query(sqlite_path: str, query_sql: str) -> List[Dict[str, Any]]:
    """Execute a single SQL query against `sqlite_path` and return rows as dicts."""
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(query_sql)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def generate_integrity_report(
    sqlite_path: str = SQLITE_DB_PATH,
    sql_path: str = SQL_SCRIPT_PATH,
    report_path: str = REPORT_JSON_PATH,
) -> Dict[str, Any]:
    """
    Run all SQL gatekeeper checks, aggregate graph telemetry, and save
    `.cirque/devlog/M1_DATA_PLANE/step_1_4_integrity_report.json`.
    """
    queries = parse_named_sql_queries(sql_path)

    orphan_rows = execute_named_query(sqlite_path, queries["orphan_edges"])
    uphill_piste_rows = execute_named_query(sqlite_path, queries["uphill_piste_violations"])
    downhill_lift_rows = execute_named_query(sqlite_path, queries["downhill_lift_violations"])
    lift_dead_end_rows = execute_named_query(sqlite_path, queries["lift_top_dead_ends"])
    isolated_service_rows = execute_named_query(sqlite_path, queries["isolated_mountain_services"])
    reachability_rows = execute_named_query(sqlite_path, queries["summit_to_base_reachability"])

    conn = sqlite3.connect(sqlite_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM nodes")
        total_nodes = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM edges")
        total_edges = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM mountain_services")
        total_services = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM edges WHERE type = 'piste'")
        piste_count = int(cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM edges WHERE type = 'lift'")
        lift_count = int(cur.fetchone()[0])
    finally:
        conn.close()

    gravity_violations = len(uphill_piste_rows) + len(downhill_lift_rows)
    orphan_edges = len(orphan_rows)
    lift_top_dead_ends = len(lift_dead_end_rows)
    isolated_services = len(isolated_service_rows)

    reachable_base_nodes = sorted(
        list({row["reached_base_node_id"] for row in reachability_rows})
    )
    summit_origins_verified = sorted(
        list({row["origin_summit_id"] for row in reachability_rows})
    )

    passed = (
        orphan_edges == 0
        and gravity_violations == 0
        and lift_top_dead_ends == 0
        and isolated_services == 0
        and "node_village_mountain_village" in reachable_base_nodes
        and len(summit_origins_verified) >= 2
    )

    report = {
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
            SQL_SCRIPT_PATH,
            "tests/pipeline/test_graph_integrity.py",
            report_path,
            DEVLOG_SQL_COPY_PATH,
        ],
        "harness_execution": {
            "name": "Comprehensive Graph Topology & Reachability Gatekeeper",
            "command": "pytest tests/pipeline/test_graph_integrity.py -v",
            "pass_criteria": "Zero orphan edges, zero negative slope gravity violations on runs, 100% reachability to mountain base.",
            "status": "PASSED" if passed else "FAILED",
        },
        "content_harvesting": {
            "sublines": "Data Quality as a First-Class Citizen in Spatial AI",
            "artifacts_to_save": [
                DEVLOG_SQL_COPY_PATH,
                report_path,
            ],
            "talking_points": [
                "Why standard graph algorithms break when ski lifts travel uphill and skiers travel downhill",
                "Using Recursive CTEs in SQLite to prove summit-to-base reachability before packaging mobile bundles",
                "Automated data quality gates that block broken topologies in CI/CD",
            ],
        },
    }

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    if os.path.exists(sql_path):
        shutil.copyfile(sql_path, DEVLOG_SQL_COPY_PATH)

    return report


@pytest.fixture(scope="module")
def verified_environment() -> Dict[str, Any]:
    """
    Ensure `data/compiled/topology.sqlite` is compiled and services are ingested,
    then parse `scripts/verify_graph_integrity.sql` and generate the integrity report.
    """
    if not os.path.exists(SQLITE_DB_PATH):
        compile_topology()
        ingest_mountain_services()
    else:
        # Ensure mountain_services is populated if topology.sqlite was rebuilt
        conn = sqlite3.connect(SQLITE_DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM mountain_services")
            if cur.fetchone()[0] == 0:
                ingest_mountain_services()
        finally:
            conn.close()

    queries = parse_named_sql_queries(SQL_SCRIPT_PATH)
    report = generate_integrity_report(SQLITE_DB_PATH, SQL_SCRIPT_PATH, REPORT_JSON_PATH)
    return {"queries": queries, "report": report}


def test_no_orphan_edges(verified_environment: Dict[str, Any]):
    """
    Check 1: Asserts that 0 edges reference non-existent source_node or target_node vertices.
    """
    queries = verified_environment["queries"]
    orphan_rows = execute_named_query(SQLITE_DB_PATH, queries["orphan_edges"])
    assert len(orphan_rows) == 0, f"Detected orphan edges with missing foreign keys: {orphan_rows}"
    assert verified_environment["report"]["orphan_edges"] == 0


def test_gravity_invariants(verified_environment: Dict[str, Any]):
    """
    Check 2: Asserts that 0 piste edges flow uphill (> 0.5% pitch or positive vertical_diff_m)
    and 0 lift edges flow downhill (vertical_diff_m <= 0).
    """
    queries = verified_environment["queries"]
    uphill_pistes = execute_named_query(SQLITE_DB_PATH, queries["uphill_piste_violations"])
    downhill_lifts = execute_named_query(SQLITE_DB_PATH, queries["downhill_lift_violations"])

    assert len(uphill_pistes) == 0, f"Unauthorized uphill ski runs detected: {uphill_pistes}"
    assert len(downhill_lifts) == 0, f"Unauthorized downhill ski lifts detected: {downhill_lifts}"
    assert verified_environment["report"]["gravity_violations"] == 0


def test_lift_summit_escapes(verified_environment: Dict[str, Any]):
    """
    Check 3: Asserts that every `lift_top` terminal node has at least one outgoing piste edge
    (no chairlift unloads into a topological dead end).
    """
    queries = verified_environment["queries"]
    dead_ends = execute_named_query(SQLITE_DB_PATH, queries["lift_top_dead_ends"])
    assert len(dead_ends) == 0, f"Lift top terminals with 0 escape routes detected: {dead_ends}"

    # Verify Mountain Services connectivity as well (Check 4)
    isolated_services = execute_named_query(SQLITE_DB_PATH, queries["isolated_mountain_services"])
    assert len(isolated_services) == 0, f"Isolated mountain services with 0 incident edges: {isolated_services}"


def test_base_lodge_reachability(verified_environment: Dict[str, Any]):
    """
    Check 5: Executes the Recursive CTE `downstream_path` query and asserts that
    both Lone Peak Summit (`node_summit_lone_peak`) and Andesite Summit (`node_jct_001`)
    can reach Mountain Village Base (`node_village_mountain_village`) via continuous downhill pistes.
    """
    queries = verified_environment["queries"]
    reachability_rows = execute_named_query(SQLITE_DB_PATH, queries["summit_to_base_reachability"])
    assert len(reachability_rows) > 0, "Recursive CTE returned 0 reachable base nodes from summits"

    # Map origin_summit_id -> set of reached base node IDs
    summit_to_bases: Dict[str, set[str]] = {}
    for row in reachability_rows:
        summit_to_bases.setdefault(row["origin_summit_id"], set()).add(row["reached_base_node_id"])

    # Assert Lone Peak Summit reaches Mountain Village Base
    assert "node_summit_lone_peak" in summit_to_bases, "Lone Peak Summit missing from reachability origins"
    assert "node_village_mountain_village" in summit_to_bases["node_summit_lone_peak"], (
        f"Lone Peak Summit cannot reach Mountain Village Base. Reached: {summit_to_bases['node_summit_lone_peak']}"
    )

    # Assert Andesite Summit (node_jct_001) reaches Mountain Village Base
    assert "node_jct_001" in summit_to_bases, "Andesite Summit (node_jct_001) missing from reachability origins"
    assert "node_village_mountain_village" in summit_to_bases["node_jct_001"], (
        f"Andesite Summit cannot reach Mountain Village Base. Reached: {summit_to_bases['node_jct_001']}"
    )

    # Verify report JSON structure and gatekeeper status
    report = verified_environment["report"]
    assert os.path.exists(REPORT_JSON_PATH), f"Integrity report must be saved at {REPORT_JSON_PATH}"
    assert report["gatekeeper_status"] == "PASSED"
    assert report["total_nodes"] >= 42
    assert report["total_edges"] >= 56
    assert report["total_services"] >= 15
    assert "node_village_mountain_village" in report["reachable_base_nodes"]
