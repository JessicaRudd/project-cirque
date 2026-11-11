#!/usr/bin/env python3
"""
Project Cirque — Standalone Web Preview Harness Server (Milestones 1–3)
Runner: pipeline/serve_preview.py

Serves `web/preview.html` on localhost, streams `data/raw/big_sky_raw.geojson`,
and queries `data/compiled/topology.sqlite` strictly in read-only mode (`?mode=ro` + `PRAGMA query_only = ON`):
  - GET /                             -> web/preview.html
  - GET /web/preview.html             -> web/preview.html
  - GET /data/raw/big_sky_raw.geojson -> Raw Big Sky pistes & lifts GeoJSON
  - GET /api/services                 -> Live `mountain_services` joined with `nodes`
  - GET /api/topology                 -> Live node/edge/service counts from topology.sqlite
"""

from __future__ import annotations

import argparse
import http.server
import json
import logging
import socketserver
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
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


def _open_readonly_db(sqlite_path: Path) -> sqlite3.Connection:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"Compiled SQLite database not found at {sqlite_path}")
    uri = f"file:{sqlite_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON;")
    return conn


def _parse_minutes(hhmm: str) -> Optional[int]:
    parts = hhmm.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hours, mins = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= hours <= 23 and 0 <= mins <= 59):
        return None
    return hours * 60 + mins


def _is_open_at(open_str: str, close_str: str, query_mins: int) -> bool:
    open_mins = _parse_minutes(open_str)
    close_mins = _parse_minutes(close_str)
    if open_mins is None or close_mins is None:
        return False
    if open_mins <= close_mins:
        return open_mins <= query_mins <= close_mins
    return query_mins >= open_mins or query_mins <= close_mins


def query_mountain_services(sqlite_path: Path = SQLITE_PATH) -> List[Dict[str, Any]]:
    conn = _open_readonly_db(sqlite_path)
    try:
        cur = conn.cursor()
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
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def query_topology_summary(sqlite_path: Path = SQLITE_PATH) -> Dict[str, Any]:
    conn = _open_readonly_db(sqlite_path)
    try:
        cur = conn.cursor()
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


class CirquePreviewRequestHandler(http.server.BaseHTTPRequestHandler):
    """Serves only allowlisted preview assets and read-only SQLite JSON endpoints."""

    def _send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status=status)

    def _serve_file(self, file_path: Path, content_type: str) -> None:
        resolved = file_path.resolve()
        if not resolved.is_relative_to(REPO_ROOT) or not resolved.is_file():
            self._send_json({"error": "Not found"}, status=404)
            return
        self._send_bytes(resolved.read_bytes(), content_type)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        req_path = parsed.path

        if req_path in ("/", "/index.html", "/preview.html", "/web", "/web/", "/web/preview.html"):
            self._serve_file(WEB_PREVIEW_PATH, "text/html; charset=utf-8")
            return

        if req_path == "/data/raw/big_sky_raw.geojson":
            self._serve_file(GEOJSON_PATH, "application/geo+json; charset=utf-8")
            return

        if req_path == "/api/services":
            try:
                services = query_mountain_services(SQLITE_PATH)
            except (FileNotFoundError, sqlite3.Error) as exc:
                logger.error("Failed querying mountain_services: %s", exc)
                self._send_json({"error": "Database unavailable"}, status=500)
                return

            query_params = parse_qs(parsed.query)
            category_filter = query_params.get("category", [None])[0]
            time_filter = query_params.get("time", [None])[0]

            if category_filter:
                services = [s for s in services if s["category"] == category_filter]
            if time_filter:
                query_mins = _parse_minutes(time_filter)
                if query_mins is None:
                    self._send_json({"error": "Invalid HH:MM time parameter"}, status=400)
                    return
                services = [
                    s for s in services
                    if _is_open_at(s["open_time_local"], s["close_time_local"], query_mins)
                ]

            self._send_json(
                {
                    "source": "data/compiled/topology.sqlite",
                    "table": "mountain_services",
                    "count": len(services),
                    "services": services,
                }
            )
            return

        if req_path == "/api/topology":
            try:
                summary = query_topology_summary(SQLITE_PATH)
            except (FileNotFoundError, sqlite3.Error) as exc:
                logger.error("Failed querying topology summary: %s", exc)
                self._send_json({"error": "Database unavailable"}, status=500)
                return
            self._send_json(summary)
            return

        self._send_json({"error": "Not found"}, status=404)


class ReusableTCPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    if not WEB_PREVIEW_PATH.exists():
        raise FileNotFoundError(f"Preview file missing at {WEB_PREVIEW_PATH}")
    services_count = len(query_mountain_services(SQLITE_PATH))

    server = ReusableTCPServer((host, port), CirquePreviewRequestHandler)
    logger.info(
        "Serving %s at http://%s:%d (%d mountain_services loaded)",
        WEB_PREVIEW_PATH.relative_to(REPO_ROOT),
        host,
        port,
        services_count,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down preview server...")
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Project Cirque web/preview.html harness.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
