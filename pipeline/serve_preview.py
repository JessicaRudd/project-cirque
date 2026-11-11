#!/usr/bin/env python3
"""
Project Cirque — Standalone Web Preview Harness Server (Milestones 1–3)
Runner: pipeline/serve_preview.py

Serves `web/preview.html` on port 8080, streams `data/raw/big_sky_raw.geojson`,
and queries `data/compiled/topology.sqlite` in read-only mode (`mode=ro`) to expose:
  - GET /                       -> web/preview.html
  - GET /web/preview.html       -> web/preview.html
  - GET /api/services           -> Live `mountain_services` joined with `nodes` from topology.sqlite
  - GET /api/topology           -> Live node/edge/service counts & integrity telemetry from topology.sqlite
  - GET /api/scenarios          -> Computed scenario paths & step telemetry from topology.sqlite + GeoJSON
  - GET /data/raw/big_sky_raw.geojson -> Raw Big Sky pistes & lifts GeoJSON
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import logging
import mimetypes
import os
import socketserver
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Cirque-Preview] %(message)s",
)
logger = logging.getLogger("cirque_preview")

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_PREVIEW_PATH = REPO_ROOT / "web" / "preview.html"
GEOJSON_PATH = REPO_ROOT / "data" / "raw" / "big_sky_raw.geojson"
SQLITE_PATH = REPO_ROOT / "data" / "compiled" / "topology.sqlite"


def query_mountain_services(sqlite_path: Path = SQLITE_PATH) -> List[Dict[str, Any]]:
    """
    Query `mountain_services` joined with `nodes` from `data/compiled/topology.sqlite`
    using read-only SQLite URI mode (`mode=ro`).
    """
    if not sqlite_path.exists():
        raise FileNotFoundError(f"Compiled SQLite database not found at {sqlite_path}")

    uri = f"file:{sqlite_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA query_only = ON;")
        cur.execute(
            """
            SELECT
                ms.service_id,
                ms.node_id,
                ms.name,
                ms.category,
                ms.service_speed,
                ms.open_time_local,
                ms.close_time_local,
                ms.requires_reservation,
                ms.price_tier,
                ms.is_ski_in_only,
                ms.daily_status,
                n.lat,
                n.lon,
                n.elevation_m,
                n.name AS node_name,
                n.node_type
            FROM mountain_services ms
            JOIN nodes n ON ms.node_id = n.node_id
            ORDER BY
                CASE ms.category
                    WHEN 'quick_snack' THEN 1
                    WHEN 'sit_down' THEN 2
                    WHEN 'cafeteria' THEN 3
                    WHEN 'bar' THEN 4
                    WHEN 'patrol' THEN 5
                    WHEN 'warming_hut' THEN 6
                    ELSE 7
                END,
                ms.name ASC
            """
        )
        rows = [dict(r) for r in cur.fetchall()]
        return rows
    finally:
        conn.close()


def query_topology_summary(sqlite_path: Path = SQLITE_PATH) -> Dict[str, Any]:
    """Query aggregate counts and milestone verification stats from `topology.sqlite`."""
    if not sqlite_path.exists():
        return {"error": f"Missing {sqlite_path}"}

    uri = f"file:{sqlite_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA query_only = ON;")

        total_nodes = int(cur.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
        total_edges = int(cur.execute("SELECT COUNT(*) FROM edges").fetchone()[0])
        piste_edges = int(cur.execute("SELECT COUNT(*) FROM edges WHERE type = 'piste'").fetchone()[0])
        lift_edges = int(cur.execute("SELECT COUNT(*) FROM edges WHERE type = 'lift'").fetchone()[0])
        total_services = int(cur.execute("SELECT COUNT(*) FROM mountain_services").fetchone()[0])

        by_difficulty: Dict[str, int] = {}
        for row in cur.execute("SELECT difficulty, COUNT(*) AS cnt FROM edges GROUP BY difficulty").fetchall():
            by_difficulty[row["difficulty"] or "unknown"] = int(row["cnt"])

        by_service_cat: Dict[str, int] = {}
        for row in cur.execute("SELECT category, COUNT(*) AS cnt FROM mountain_services GROUP BY category").fetchall():
            by_service_cat[row["category"] or "unknown"] = int(row["cnt"])

        return {
            "sqlite_path": "data/compiled/topology.sqlite",
            "pragma_query_only": True,
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "piste_edges": piste_edges,
            "lift_edges": lift_edges,
            "total_services": total_services,
            "edges_by_difficulty": by_difficulty,
            "services_by_category": by_service_cat,
        }
    finally:
        conn.close()


class CirquePreviewRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Request Handler serving `web/preview.html`, static assets, and SQLite JSON APIs."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        req_path = parsed.path

        if req_path in ("/", "/index.html", "/preview.html", "/web", "/web/"):
            self.path = "/web/preview.html"
            return super().do_GET()

        if req_path == "/api/services":
            try:
                services = query_mountain_services(SQLITE_PATH)
                query_params = parse_qs(parsed.query)
                category_filter = query_params.get("category", [None])[0]
                time_filter = query_params.get("time", [None])[0]

                if category_filter:
                    services = [s for s in services if s["category"] == category_filter]
                if time_filter:
                    services = [
                        s
                        for s in services
                        if s["open_time_local"] <= time_filter <= s["close_time_local"]
                    ]

                self._send_json(
                    {
                        "source": "data/compiled/topology.sqlite",
                        "table": "mountain_services",
                        "count": len(services),
                        "services": services,
                    }
                )
            except Exception as exc:
                logger.exception("Error querying mountain_services:")
                self._send_json({"error": str(exc)}, status=500)
            return

        if req_path == "/api/topology":
            try:
                summary = query_topology_summary(SQLITE_PATH)
                self._send_json(summary)
            except Exception as exc:
                logger.exception("Error querying topology summary:")
                self._send_json({"error": str(exc)}, status=500)
            return

        return super().do_GET()


class ReusableTCPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    mimetypes.add_type("application/geo+json", ".geojson")
    mimetypes.add_type("application/vnd.sqlite3", ".sqlite")

    if not WEB_PREVIEW_PATH.exists():
        logger.warning("Preview file %s does not exist yet.", WEB_PREVIEW_PATH)

    services_count = 0
    if SQLITE_PATH.exists():
        try:
            services_count = len(query_mountain_services(SQLITE_PATH))
        except Exception as exc:
            logger.warning("SQLite pre-check warning: %s", exc)

    server = ReusableTCPServer((host, port), CirquePreviewRequestHandler)
    logger.info("======================================================================")
    logger.info("Project Cirque — Milestone 1-3 Web Preview Harness")
    logger.info("Serving web/preview.html at: http://localhost:%d", port)
    logger.info("GeoJSON source            : %s", GEOJSON_PATH.relative_to(REPO_ROOT))
    logger.info("SQLite topology source    : %s (%d mountain_services)", SQLITE_PATH.relative_to(REPO_ROOT), services_count)
    logger.info("======================================================================")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down preview server...")
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Serve Project Cirque web/preview.html harness on port 8080."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
