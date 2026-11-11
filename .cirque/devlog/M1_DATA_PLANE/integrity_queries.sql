-- ============================================================================
-- Project Cirque: Spatial Data Integrity Harness (Milestone 1, Step 1.4)
-- File: scripts/verify_graph_integrity.sql
-- Target Database: data/compiled/topology.sqlite
-- Specification: TECH_SPEC.md Section 2.3, 2.4 & Stage 1.4
-- ============================================================================

-- @query: orphan_edges
-- 1. Orphan Edge & Missing Foreign Key Check
-- Identifies any edge where source_node or target_node does not exist in nodes.
-- Pass Criterion: Must return 0 rows.
SELECT
    e.edge_id,
    e.name,
    e.source_node,
    e.target_node
FROM edges e
LEFT JOIN nodes src ON e.source_node = src.node_id
LEFT JOIN nodes dst ON e.target_node = dst.node_id
WHERE src.node_id IS NULL
   OR dst.node_id IS NULL;

-- @query: uphill_piste_violations
-- 2a. Gravity Polarity & Elevation Invariant (Pistes)
-- Identifies any piste edge where source_node.elevation_m < target_node.elevation_m
-- AND average_pitch_pct > 0.5% (unauthorized uphill ski runs).
-- Pass Criterion: Must return 0 rows.
SELECT
    e.edge_id,
    e.name,
    e.source_node,
    src.elevation_m AS source_elevation_m,
    e.target_node,
    dst.elevation_m AS target_elevation_m,
    e.vertical_diff_m,
    e.average_pitch_pct
FROM edges e
JOIN nodes src ON e.source_node = src.node_id
JOIN nodes dst ON e.target_node = dst.node_id
WHERE e.type = 'piste'
  AND (
      (src.elevation_m < dst.elevation_m AND e.average_pitch_pct > 0.5)
      OR e.vertical_diff_m > 0.0
  );

-- @query: downhill_lift_violations
-- 2b. Gravity Polarity & Elevation Invariant (Lifts)
-- Identifies any lift edge where source_node.elevation_m >= target_node.elevation_m.
-- Pass Criterion: Must return 0 rows.
SELECT
    e.edge_id,
    e.name,
    e.source_node,
    src.elevation_m AS source_elevation_m,
    e.target_node,
    dst.elevation_m AS target_elevation_m,
    e.vertical_diff_m
FROM edges e
JOIN nodes src ON e.source_node = src.node_id
JOIN nodes dst ON e.target_node = dst.node_id
WHERE e.type = 'lift'
  AND (src.elevation_m >= dst.elevation_m OR e.vertical_diff_m <= 0.0);

-- @query: lift_top_dead_ends
-- 3. Lift Top Terminal Escape Route Check
-- Identifies any node with node_type = 'lift_top' that has zero outgoing piste edges.
-- Pass Criterion: Must return 0 rows.
SELECT
    n.node_id,
    n.name,
    n.elevation_m,
    COUNT(e.edge_id) AS outgoing_piste_edges
FROM nodes n
LEFT JOIN edges e
    ON n.node_id = e.source_node
   AND e.type = 'piste'
WHERE n.node_type = 'lift_top'
GROUP BY n.node_id, n.name, n.elevation_m
HAVING COUNT(e.edge_id) = 0;

-- @query: isolated_mountain_services
-- 4. Mountain Services Connectivity Check
-- Identifies any service_id in mountain_services where the associated node_id
-- is an isolated island with 0 incident edges (neither source nor target).
-- Pass Criterion: Must return 0 rows.
SELECT
    ms.service_id,
    ms.name AS service_name,
    ms.category,
    ms.node_id,
    COUNT(e.edge_id) AS incident_edge_count
FROM mountain_services ms
LEFT JOIN edges e
    ON ms.node_id = e.source_node
    OR ms.node_id = e.target_node
GROUP BY ms.service_id, ms.name, ms.category, ms.node_id
HAVING COUNT(e.edge_id) = 0;

-- @query: summit_to_base_reachability
-- 5. Summit-to-Base Reachability Proof (Recursive CTE)
-- Traces continuous downhill piste paths starting from Lone Peak Summit
-- (node_type = 'summit') and Andesite Summit ('node_jct_001')
-- down to base destinations (node_type IN ('village', 'lift_base')).
-- Pass Criterion: Both summits must reach Mountain Village Base ('node_village_mountain_village').
WITH RECURSIVE summit_origins AS (
    SELECT
        node_id AS origin_summit_id,
        name AS origin_summit_name
    FROM nodes
    WHERE node_type = 'summit'
       OR node_id = 'node_jct_001'
),
downstream_path(origin_summit_id, origin_summit_name, current_node_id, hops, visited_path) AS (
    SELECT
        origin_summit_id,
        origin_summit_name,
        origin_summit_id AS current_node_id,
        0 AS hops,
        '->' || origin_summit_id || '->' AS visited_path
    FROM summit_origins

    UNION ALL

    SELECT
        dp.origin_summit_id,
        dp.origin_summit_name,
        e.target_node AS current_node_id,
        dp.hops + 1 AS hops,
        dp.visited_path || e.target_node || '->' AS visited_path
    FROM downstream_path dp
    JOIN edges e
        ON dp.current_node_id = e.source_node
       AND e.type = 'piste'
    WHERE dp.hops < 25
      AND INSTR(dp.visited_path, '->' || e.target_node || '->') = 0
)
SELECT
    dp.origin_summit_id,
    dp.origin_summit_name,
    n.node_id AS reached_base_node_id,
    n.name AS reached_base_name,
    n.node_type AS reached_base_type,
    MIN(dp.hops) AS min_hops
FROM downstream_path dp
JOIN nodes n ON dp.current_node_id = n.node_id
WHERE n.node_type IN ('village', 'lift_base')
GROUP BY
    dp.origin_summit_id,
    dp.origin_summit_name,
    n.node_id,
    n.name,
    n.node_type
ORDER BY dp.origin_summit_id, n.node_id;
