---
name: cirque-topology-inspector
description: Query and inspect Big Sky topology.sqlite and raw GeoJSON geometries using bounded, token-efficient queries to avoid context window exhaustion.
---
# Cirque Topology Inspector

Use this skill when verifying graph connectivity, node IDs, slope percentages, or amenity coordinates in Big Sky Resort data.

## 1. Token Safety Rules
- **NEVER** run `cat`, `view_file`, or unbounded `grep` on `data/raw/big_sky_raw.geojson` (71,825 lines).
- **NEVER** run `SELECT * FROM edges` or `SELECT * FROM nodes` without a `LIMIT` clause.
- Always use specific, indexed queries to keep tool outputs under 50 lines.

## 2. Standard Query Patterns
- **Inspect Specific Node by ID or Name:**
  ```bash
  sqlite3 data/compiled/topology.sqlite "SELECT node_id, name, elevation_m, node_type, poi_category FROM nodes WHERE node_id = '<id>' OR name LIKE '%<name>%' LIMIT 5;"
  ```
- **Inspect Outgoing Edges from a Node:**
  ```bash
  sqlite3 data/compiled/topology.sqlite "SELECT edge_id, name, type, difficulty, grooming, length_m, vertical_diff_m, base_cost_seconds FROM edges WHERE source_node = '<node_id>' ORDER BY base_cost_seconds ASC LIMIT 10;"
  ```
- **Inspect Mountain Services (Dining / Patrol / Warming Huts):**
  ```bash
  sqlite3 data/compiled/topology.sqlite "SELECT service_id, node_id, name, category, service_speed, open_time_local, close_time_local, requires_reservation, daily_status FROM mountain_services WHERE category = '<category>' LIMIT 10;"
  ```
- **Targeted GeoJSON Inspection via `jq`:**
  ```bash
  jq -c '.features[] | select(.properties.name == "<Trail or Lift Name>") | {type: .geometry.type, props: .properties}' data/raw/big_sky_raw.geojson | head -n 5
  ```
