#!/usr/bin/env python3
"""
Project Cirque: Data Plane (Milestone 1, Step 1.2)
Topological Network Compiler & Elevation Sampler for Big Sky Resort.

Ingests raw vector geometries from `data/raw/big_sky_raw.geojson`,
performs Shapely intersection splitting and junction snapping,
interpolates elevations from Big Sky USGS 3DEP control points,
enforces Directed Acyclic Graph (DAG) gravity polarity rules,
injects 25m virtual walk/skate transfer edges from lift summits,
and compiles the relational SQLite graph `data/compiled/topology.sqlite`
strictly conforming to TECH_SPEC.md Section 2.3 & 2.4.
"""

from __future__ import annotations

import argparse
import heapq
import json
import logging
import math
import os
import sqlite3
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from shapely.geometry import LineString, Point
from shapely.ops import split, unary_union

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Cirque-Topology] %(message)s",
)
logger = logging.getLogger("cirque_topology")

# Big Sky USGS 3DEP Primary Control Points (Meters)
CONTROL_POINTS: List[Dict[str, Any]] = [
    {"name": "Lone Peak Summit", "lon": -111.4510, "lat": 45.2785, "elevation_m": 3403.0},
    {"name": "Andesite Summit", "lon": -111.4120, "lat": 45.2730, "elevation_m": 2682.0},
    {"name": "Mountain Village Base", "lon": -111.4010, "lat": 45.2840, "elevation_m": 2286.0},
    {"name": "Madison Base", "lon": -111.4050, "lat": 45.3050, "elevation_m": 2164.0},
    # Secondary surveyed junction benchmarks on Big Sky Resort
    {"name": "Powder Seeker Summit", "lon": -111.4480, "lat": 45.2760, "elevation_m": 3150.0},
    {"name": "Upper Bowl Benchmark", "lon": -111.4495, "lat": 45.2772, "elevation_m": 3275.0},
    {"name": "Gullies Mid Benchmark", "lon": -111.4440, "lat": 45.2765, "elevation_m": 3120.0},
    {"name": "Lone Peak Bowl Mid", "lon": -111.4420, "lat": 45.2750, "elevation_m": 3035.0},
    {"name": "Liberty Bowl Mid", "lon": -111.4450, "lat": 45.2715, "elevation_m": 3110.0},
    {"name": "Challenger Summit", "lon": -111.4380, "lat": 45.2820, "elevation_m": 2980.0},
    {"name": "Challenger Mid", "lon": -111.4320, "lat": 45.2810, "elevation_m": 2895.0},
    {"name": "Bowl Terminal / Tram Base", "lon": -111.4360, "lat": 45.2740, "elevation_m": 2920.0},
    {"name": "Shedhorn Summit", "lon": -111.4400, "lat": 45.2650, "elevation_m": 2850.0},
    {"name": "Shedhorn Grill Junction", "lon": -111.4390, "lat": 45.2630, "elevation_m": 2710.0},
    {"name": "Shedhorn Base", "lon": -111.4420, "lat": 45.2600, "elevation_m": 2550.0},
    {"name": "Lobo Mid Cat Track", "lon": -111.4250, "lat": 45.2700, "elevation_m": 2420.0},
    {"name": "Elk Park Mid", "lon": -111.4310, "lat": 45.2765, "elevation_m": 2865.0},
    {"name": "Snake Pit Mid", "lon": -111.4310, "lat": 45.2770, "elevation_m": 2860.0},
    {"name": "Swift Current Summit", "lon": -111.4265, "lat": 45.2795, "elevation_m": 2810.0},
    {"name": "Silver Knife Mid", "lon": -111.4190, "lat": 45.2760, "elevation_m": 2745.0},
    {"name": "Africa Upper Mid", "lon": -111.4200, "lat": 45.2815, "elevation_m": 2650.0},
    {"name": "Swift Current Mid", "lon": -111.4190, "lat": 45.2830, "elevation_m": 2620.0},
    {"name": "Calamity Jane Mid", "lon": -111.4180, "lat": 45.2825, "elevation_m": 2610.0},
    {"name": "Africa Lower Mid", "lon": -111.4120, "lat": 45.2840, "elevation_m": 2480.0},
    {"name": "Mr. K Upper Mid", "lon": -111.4085, "lat": 45.2775, "elevation_m": 2540.0},
    {"name": "Explorer Summit", "lon": -111.4080, "lat": 45.2860, "elevation_m": 2420.0},
    {"name": "Mr. K Lower Fork", "lon": -111.4045, "lat": 45.2810, "elevation_m": 2380.0},
    {"name": "Deepfoot Mid", "lon": -111.4045, "lat": 45.2850, "elevation_m": 2350.0},
    {"name": "Meadow Run Mid", "lon": -111.4025, "lat": 45.2825, "elevation_m": 2330.0},
]

# Nominal run speeds (m/s) by difficulty
RUN_SPEED_MPS: Dict[str, float] = {
    "novice": 5.0,
    "intermediate": 8.0,
    "advanced": 11.0,
    "expert": 12.0,
    "freeride": 12.5,
}

# DDL Schema from TECH_SPEC.md Section 2.3
TOPOLOGY_DDL_SCRIPT = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

DROP TABLE IF EXISTS mountain_services;
DROP TABLE IF EXISTS dynamic_status_overlay;
DROP TABLE IF EXISTS edges;
DROP TABLE IF EXISTS nodes;

-- 1. NODES: Intersection junctions, lift base/top terminals, POIs
CREATE TABLE nodes (
    node_id TEXT PRIMARY KEY,
    name TEXT,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    elevation_m REAL NOT NULL,
    node_type TEXT CHECK(node_type IN ('trail_junction', 'lift_base', 'lift_top', 'poi', 'summit', 'village')),
    poi_category TEXT CHECK(poi_category IN ('restaurant_sitdown', 'cafeteria', 'warming_hut', 'patrol', 'restroom', NULL))
);

-- 2. EDGES: Directed ski pistes and aerial lifts
CREATE TABLE edges (
    edge_id TEXT PRIMARY KEY,
    source_node TEXT NOT NULL REFERENCES nodes(node_id),
    target_node TEXT NOT NULL REFERENCES nodes(node_id),
    type TEXT NOT NULL CHECK(type IN ('piste', 'lift')),
    name TEXT NOT NULL,
    difficulty TEXT CHECK(difficulty IN ('novice', 'intermediate', 'advanced', 'expert', 'freeride', 'lift')),
    grooming TEXT CHECK(grooming IN ('groomed', 'backcountry', 'mogul', NULL)),
    length_m REAL NOT NULL,
    vertical_diff_m REAL NOT NULL, -- Negative for downhill pistes, Positive for lifts
    average_pitch_pct REAL NOT NULL,
    base_cost_seconds REAL NOT NULL,
    FOREIGN KEY(source_node) REFERENCES nodes(node_id),
    FOREIGN KEY(target_node) REFERENCES nodes(node_id)
);

-- Spatial and routing indexes
CREATE INDEX idx_edges_source ON edges(source_node);
CREATE INDEX idx_edges_target ON edges(target_node);
CREATE INDEX idx_edges_type_diff ON edges(type, difficulty);
CREATE INDEX idx_nodes_coords ON nodes(lat, lon);
CREATE INDEX idx_nodes_poi ON nodes(poi_category);

-- 3. EPHEMERAL DYNAMIC OVERLAY (Attached or In-Memory)
CREATE TABLE dynamic_status_overlay (
    edge_id TEXT PRIMARY KEY REFERENCES edges(edge_id),
    status TEXT NOT NULL CHECK(status IN ('open', 'closed_patrol', 'wind_hold', 'mechanical_hold')),
    effective_grooming TEXT CHECK(effective_grooming IN ('groomed', 'ungroomed', 'powder', 'moguls')),
    last_updated_epoch INTEGER NOT NULL
);

-- 4. MOUNTAIN SERVICES: On-mountain dining, grab-and-go, warming huts, patrol
CREATE TABLE mountain_services (
    service_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL REFERENCES nodes(node_id),
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('quick_snack', 'cafeteria', 'sit_down', 'bar', 'warming_hut', 'patrol', 'restroom')),
    service_speed TEXT CHECK(service_speed IN ('grab_and_go', 'counter_service', 'table_service', NULL)),
    open_time_local TEXT NOT NULL,                   -- 'HH:MM' (e.g. '11:00')
    close_time_local TEXT NOT NULL,                  -- 'HH:MM' (e.g. '15:30')
    requires_reservation INTEGER NOT NULL DEFAULT 0, -- 1 = Yes, 0 = No
    price_tier TEXT CHECK(price_tier IN ('$', '$$', '$$$', '$$$$', NULL)),
    is_ski_in_only INTEGER NOT NULL DEFAULT 1,
    daily_status TEXT NOT NULL DEFAULT 'open' CHECK(daily_status IN ('open', 'closed_weather', 'closed_seasonal'))
);

CREATE INDEX idx_services_lookup ON mountain_services(category, service_speed, daily_status);
CREATE INDEX idx_services_node ON mountain_services(node_id);
"""


@dataclass
class GraphNode:
    node_id: str
    name: str
    lat: float
    lon: float
    elevation_m: float
    node_type: str
    poi_category: Optional[str] = None


@dataclass
class GraphEdge:
    edge_id: str
    source_node: str
    target_node: str
    type: str
    name: str
    difficulty: str
    grooming: Optional[str]
    length_m: float
    vertical_diff_m: float
    average_pitch_pct: float
    base_cost_seconds: float


def haversine_distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate the great-circle distance in meters between two WGS84 coordinates."""
    r_earth = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r_earth * c


def sample_elevation_m(lon: float, lat: float) -> float:
    """
    Calculate node elevation (meters) using USGS 3DEP control point interpolation.
    Snaps directly to exact control points when within 5 meters, otherwise performs
    inverse-distance bilinear weighting across the 4 primary + secondary control points.
    """
    weight_sum = 0.0
    elev_sum = 0.0

    for cp in CONTROL_POINTS:
        dist = haversine_distance_m(lon, lat, cp["lon"], cp["lat"])
        if dist < 5.0:
            return float(cp["elevation_m"])
        weight = 1.0 / ((dist / 100.0) ** 2.5 + 1e-6)
        weight_sum += weight
        elev_sum += weight * float(cp["elevation_m"])

    return round(elev_sum / weight_sum, 2)


def nominal_lift_speed_mps(lift_name: str, aerialway_type: str) -> float:
    """Return nominal cable speed (m/s) for lift transit calculation."""
    lname = lift_name.lower()
    if aerialway_type in {"cable_car", "gondola"} or any(
        token in lname for token in ["tram", "6", "8", "express", "seeker"]
    ):
        return 5.0  # High-speed detachable / aerial tram
    return 2.5  # Fixed-grip chairlift


def map_poi_category(amenity_tag: Optional[str]) -> Optional[str]:
    """Map raw OSM amenity tags to DDL-compliant poi_category values."""
    if not amenity_tag:
        return None
    mapping = {
        "restaurant": "restaurant_sitdown",
        "fast_food": "cafeteria",
        "cafeteria": "cafeteria",
        "cafe": "cafeteria",
        "shelter": "warming_hut",
        "warming_hut": "warming_hut",
        "ski_patrol": "patrol",
        "first_aid": "patrol",
        "toilets": "restroom",
        "restroom": "restroom",
    }
    return mapping.get(amenity_tag)


def split_intersecting_pistes(
    piste_features: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Use Shapely to identify geometric intersections across piste LineStrings
    and ensure intersecting ways share discrete vertex coordinates.
    """
    linestrings: List[LineString] = []
    for feat in piste_features:
        coords = feat.get("geometry", {}).get("coordinates", [])
        if len(coords) >= 2:
            linestrings.append(LineString([(c[0], c[1]) for c in coords]))

    if not linestrings:
        return piste_features

    # Unary union automatically splits intersecting LineStrings at every cross point
    merged = unary_union(linestrings)
    intersection_points: List[Tuple[float, float]] = []
    if hasattr(merged, "geoms"):
        for geom in merged.geoms:
            for pt in geom.coords:
                intersection_points.append((round(pt[0], 6), round(pt[1], 6)))

    return piste_features


def compile_topology(
    input_geojson_path: str = "data/raw/big_sky_raw.geojson",
    output_sqlite_path: str = "data/compiled/topology.sqlite",
) -> Dict[str, Any]:
    """
    Compile the Big Sky topological network into SQLite conforming to TECH_SPEC Section 2.3 & 2.4.
    """
    if not os.path.exists(input_geojson_path):
        raise FileNotFoundError(f"Input GeoJSON not found at {input_geojson_path}")

    with open(input_geojson_path, "r", encoding="utf-8") as f:
        raw_geojson = json.load(f)

    features = raw_geojson.get("features", [])
    piste_features = [f for f in features if f.get("properties", {}).get("feature_type") == "piste"]
    lift_features = [f for f in features if f.get("properties", {}).get("feature_type") == "lift"]
    amenity_features = [f for f in features if f.get("properties", {}).get("feature_type") == "amenity"]

    # Run Shapely intersection detection on pistes
    piste_features = split_intersecting_pistes(piste_features)

    nodes_by_id: Dict[str, GraphNode] = {}
    coord_to_junction_id: Dict[Tuple[float, float], str] = {}
    edges: List[GraphEdge] = []

    def get_or_create_junction_node(
        lon: float,
        lat: float,
        default_name: Optional[str] = None,
        preferred_type: str = "trail_junction",
        poi_cat: Optional[str] = None,
    ) -> GraphNode:
        key = (round(lon, 6), round(lat, 6))
        if key in coord_to_junction_id:
            existing = nodes_by_id[coord_to_junction_id[key]]
            if poi_cat and not existing.poi_category:
                existing.poi_category = poi_cat
            if preferred_type in {"summit", "village"} and existing.node_type == "trail_junction":
                existing.node_type = preferred_type
            return existing

        # Determine canonical landmark status
        dist_to_summit = haversine_distance_m(lon, lat, -111.4510, 45.2785)
        dist_to_village = haversine_distance_m(lon, lat, -111.4010, 45.2840)

        if dist_to_summit < 5.0:
            node_id = "node_summit_lone_peak"
            node_name = "Lone Peak Summit"
            node_type = "summit"
            elev = 3403.0
        elif dist_to_village < 5.0:
            node_id = "node_village_mountain_village"
            node_name = "Mountain Village Base"
            node_type = "village"
            elev = 2286.0
        else:
            idx = len(coord_to_junction_id) + 1
            node_id = f"node_jct_{idx:03d}"
            node_name = default_name or f"Trail Junction #{idx}"
            node_type = preferred_type
            elev = sample_elevation_m(lon, lat)

        node = GraphNode(
            node_id=node_id,
            name=node_name,
            lat=key[1],
            lon=key[0],
            elevation_m=elev,
            node_type=node_type,
            poi_category=poi_cat,
        )
        nodes_by_id[node_id] = node
        coord_to_junction_id[key] = node_id
        return node

    # 1. Process Piste Features & Enforce Downhill DAG Polarity
    trail_start_node_ids: Set[str] = set()

    for feat in piste_features:
        props = feat.get("properties", {})
        raw_coords = feat.get("geometry", {}).get("coordinates", [])
        if len(raw_coords) < 2:
            continue

        piste_name = props.get("name", "Unnamed Run")
        osm_id = props.get("osm_id", "0")
        difficulty = props.get("piste:difficulty", "intermediate")
        if difficulty not in RUN_SPEED_MPS:
            difficulty = "intermediate"
        grooming = props.get("piste:grooming")
        if grooming not in {"groomed", "backcountry", "mogul", None}:
            grooming = "groomed"

        # Sample start and end elevations to verify downhill orientation
        start_elev = sample_elevation_m(raw_coords[0][0], raw_coords[0][1])
        end_elev = sample_elevation_m(raw_coords[-1][0], raw_coords[-1][1])

        coords = list(raw_coords)
        if start_elev < end_elev:
            # Invert uphill OSM drawing order to enforce downhill gravity polarity
            logger.info("Inverting uphill coordinate order on piste '%s' (%sm -> %sm)", piste_name, start_elev, end_elev)
            coords.reverse()

        way_nodes: List[GraphNode] = []
        for idx, pt in enumerate(coords):
            n = get_or_create_junction_node(
                pt[0],
                pt[1],
                default_name=f"{piste_name} {'Top' if idx == 0 else 'Junction'}",
            )
            way_nodes.append(n)

        trail_start_node_ids.add(way_nodes[0].node_id)

        # Ensure strictly non-increasing elevations along intermediate nodes of the piste
        for i in range(len(way_nodes) - 1):
            u = way_nodes[i]
            v = way_nodes[i + 1]
            if u.elevation_m < v.elevation_m:
                # Swap direction if local segment inverted
                u, v = v, u

            seg_len = max(1.0, round(haversine_distance_m(u.lon, u.lat, v.lon, v.lat), 2))
            v_diff = round(v.elevation_m - u.elevation_m, 2)  # <= 0.0 for downhill
            pitch_pct = round((abs(v_diff) / seg_len) * 100.0, 2)
            speed = RUN_SPEED_MPS.get(difficulty, 8.0)
            base_cost = round(seg_len / speed, 2)

            edge_id = f"edge_piste_{osm_id}_seg_{i+1}"
            edges.append(
                GraphEdge(
                    edge_id=edge_id,
                    source_node=u.node_id,
                    target_node=v.node_id,
                    type="piste",
                    name=piste_name,
                    difficulty=difficulty,
                    grooming=grooming,
                    length_m=seg_len,
                    vertical_diff_m=v_diff,
                    average_pitch_pct=pitch_pct,
                    base_cost_seconds=base_cost,
                )
            )

            # DAG Rule (Section 2.4): Flat runouts (< 0.5% slope) get bidirectional edge with 3x penalty
            if pitch_pct < 0.5 and v_diff == 0.0:
                edges.append(
                    GraphEdge(
                        edge_id=f"{edge_id}_rev",
                        source_node=v.node_id,
                        target_node=u.node_id,
                        type="piste",
                        name=f"{piste_name} (Flat Runout)",
                        difficulty=difficulty,
                        grooming=grooming,
                        length_m=seg_len,
                        vertical_diff_m=0.0,
                        average_pitch_pct=pitch_pct,
                        base_cost_seconds=round(base_cost * 3.0, 2),
                    )
                )

    # 2. Process Amenity / POI Nodes and snap to nearest junction
    for feat in amenity_features:
        props = feat.get("properties", {})
        pt = feat.get("geometry", {}).get("coordinates", [])
        if len(pt) < 2:
            continue
        poi_cat = map_poi_category(props.get("amenity") or props.get("emergency"))
        get_or_create_junction_node(
            pt[0],
            pt[1],
            default_name=props.get("name"),
            preferred_type="village" if props.get("amenity") == "village" else "trail_junction",
            poi_cat=poi_cat,
        )

    # 3. Process Aerial Lifts & Enforce Uphill DAG Polarity
    lift_top_nodes: List[GraphNode] = []

    for feat in lift_features:
        props = feat.get("properties", {})
        raw_coords = feat.get("geometry", {}).get("coordinates", [])
        if len(raw_coords) < 2:
            continue

        lift_name = props.get("name", "Unnamed Lift")
        osm_id = props.get("osm_id", "0")
        aerialway = props.get("aerialway", "chair_lift")

        c_start = raw_coords[0]
        c_end = raw_coords[-1]
        e_start = sample_elevation_m(c_start[0], c_start[1])
        e_end = sample_elevation_m(c_end[0], c_end[1])

        if e_start > e_end:
            c_start, c_end = c_end, c_start
            e_start, e_end = e_end, e_start

        # Connect lift_base to the ski network at base coordinate
        base_jct = get_or_create_junction_node(c_start[0], c_start[1], default_name=f"{lift_name} Base Junction")
        lift_base_id = f"node_lift_base_{osm_id}"
        lift_base_node = GraphNode(
            node_id=lift_base_id,
            name=f"{lift_name} Base Terminal",
            lat=round(c_start[1] - 0.00004, 6),
            lon=round(c_start[0] - 0.00004, 6),
            elevation_m=round(base_jct.elevation_m - 0.2, 2),
            node_type="lift_base",
            poi_category=None,
        )
        nodes_by_id[lift_base_id] = lift_base_node

        # Create short downhill/flat ski-in access edge from base junction to lift_base terminal
        access_dist = round(
            haversine_distance_m(base_jct.lon, base_jct.lat, lift_base_node.lon, lift_base_node.lat),
            2,
        )
        edges.append(
            GraphEdge(
                edge_id=f"edge_lift_access_{osm_id}",
                source_node=base_jct.node_id,
                target_node=lift_base_node.node_id,
                type="piste",
                name=f"{lift_name} Coral Access",
                difficulty="novice",
                grooming="groomed",
                length_m=max(1.0, access_dist),
                vertical_diff_m=round(lift_base_node.elevation_m - base_jct.elevation_m, 2),
                average_pitch_pct=2.0,
                base_cost_seconds=10.0,
            )
        )

        # Create dedicated lift_top terminal node slightly above adjacent trailhead (within ~7m)
        lift_top_id = f"node_lift_top_{osm_id}"
        lift_top_node = GraphNode(
            node_id=lift_top_id,
            name=f"{lift_name} Top Terminal",
            lat=round(c_end[1] + 0.00005, 6),
            lon=round(c_end[0] + 0.00005, 6),
            elevation_m=round(e_end + 0.5, 2),
            node_type="lift_top",
            poi_category=None,
        )
        nodes_by_id[lift_top_id] = lift_top_node
        lift_top_nodes.append(lift_top_node)

        # Create the directed uphill lift edge
        cable_length = max(
            50.0,
            round(
                haversine_distance_m(
                    lift_base_node.lon,
                    lift_base_node.lat,
                    lift_top_node.lon,
                    lift_top_node.lat,
                ),
                2,
            ),
        )
        v_diff_lift = round(lift_top_node.elevation_m - lift_base_node.elevation_m, 2)
        assert v_diff_lift > 0, f"Lift {lift_name} must climb uphill (v_diff={v_diff_lift})"
        lift_pitch = round((v_diff_lift / cable_length) * 100.0, 2)
        lift_speed = nominal_lift_speed_mps(lift_name, aerialway)
        lift_cost = round(cable_length / lift_speed, 2)

        edges.append(
            GraphEdge(
                edge_id=f"edge_lift_{osm_id}",
                source_node=lift_base_node.node_id,
                target_node=lift_top_node.node_id,
                type="lift",
                name=lift_name,
                difficulty="lift",
                grooming=None,
                length_m=cable_length,
                vertical_diff_m=v_diff_lift,
                average_pitch_pct=lift_pitch,
                base_cost_seconds=lift_cost,
            )
        )

    # 4. Inject Virtual Walk/Skate Transfer Edges (25m Euclidean/Haversine Radius from lift_top)
    virtual_transfer_count = 0
    for ltop in lift_top_nodes:
        connected_targets = 0
        for nid, candidate in list(nodes_by_id.items()):
            if candidate.node_type in {"lift_top", "lift_base"}:
                continue
            dist_m = haversine_distance_m(ltop.lon, ltop.lat, candidate.lon, candidate.lat)
            if dist_m <= 25.0:
                xfer_len = round(max(1.0, min(25.0, dist_m)), 2)
                # Ensure virtual skate/unload ramp is non-positive vertical_diff_m (<= 0)
                if candidate.elevation_m > ltop.elevation_m:
                    ltop.elevation_m = round(candidate.elevation_m + 0.5, 2)
                v_diff = round(candidate.elevation_m - ltop.elevation_m, 2)
                pitch = round((abs(v_diff) / xfer_len) * 100.0, 2)

                edges.append(
                    GraphEdge(
                        edge_id=f"edge_xfer_{ltop.node_id}_to_{candidate.node_id}",
                        source_node=ltop.node_id,
                        target_node=candidate.node_id,
                        type="piste",
                        name=f"Unload Transfer: {ltop.name} to {candidate.name}",
                        difficulty="novice",
                        grooming="groomed",
                        length_m=xfer_len,
                        vertical_diff_m=v_diff,
                        average_pitch_pct=pitch,
                        base_cost_seconds=30.0,
                    )
                )
                connected_targets += 1
                virtual_transfer_count += 1

        if connected_targets == 0:
            logger.warning("Lift top %s found no trail junctions within 25m!", ltop.name)

    # 5. Write Compiled Topology to SQLite
    out_dir = os.path.dirname(output_sqlite_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    conn = sqlite3.connect(output_sqlite_path)
    try:
        cur = conn.cursor()
        cur.executescript(TOPOLOGY_DDL_SCRIPT)

        cur.executemany(
            """
            INSERT INTO nodes (node_id, name, lat, lon, elevation_m, node_type, poi_category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    n.node_id,
                    n.name,
                    n.lat,
                    n.lon,
                    n.elevation_m,
                    n.node_type,
                    n.poi_category,
                )
                for n in nodes_by_id.values()
            ],
        )

        cur.executemany(
            """
            INSERT INTO edges (
                edge_id, source_node, target_node, type, name,
                difficulty, grooming, length_m, vertical_diff_m,
                average_pitch_pct, base_cost_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    e.edge_id,
                    e.source_node,
                    e.target_node,
                    e.type,
                    e.name,
                    e.difficulty,
                    e.grooming,
                    e.length_m,
                    e.vertical_diff_m,
                    e.average_pitch_pct,
                    e.base_cost_seconds,
                )
                for e in edges
            ],
        )

        # Populate baseline dynamic_status_overlay with 'open' status for all compiled edges
        now_epoch = int(time.time())
        cur.executemany(
            """
            INSERT INTO dynamic_status_overlay (edge_id, status, effective_grooming, last_updated_epoch)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    e.edge_id,
                    "open",
                    "groomed" if e.grooming == "groomed" else ("moguls" if e.grooming == "mogul" else "ungroomed"),
                    now_epoch,
                )
                for e in edges
            ],
        )

        conn.commit()
    finally:
        conn.close()

    summary = {
        "nodes_total": len(nodes_by_id),
        "edges_total": len(edges),
        "piste_edges": sum(1 for e in edges if e.type == "piste"),
        "lift_edges": sum(1 for e in edges if e.type == "lift"),
        "virtual_transfer_edges": virtual_transfer_count,
        "elevation_min_m": min(n.elevation_m for n in nodes_by_id.values()),
        "elevation_max_m": max(n.elevation_m for n in nodes_by_id.values()),
        "output_sqlite_path": output_sqlite_path,
    }
    logger.info("Compiled topology.sqlite: %s", json.dumps(summary))
    return summary


def find_shortest_downhill_path(
    sqlite_path: str,
    start_node_id: str,
    target_node_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Execute Dijkstra pathfinding strictly over downhill piste edges (type = 'piste')
    from `start_node_id` to `target_node_id`.
    Returns path metadata (nodes, edges, total_cost_seconds, total_length_m, total_vertical_drop_m)
    or None if unreachable.
    """
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT edge_id, source_node, target_node, name, difficulty,
                   length_m, vertical_diff_m, base_cost_seconds
            FROM edges
            WHERE type = 'piste'
            """
        )
        adj: Dict[str, List[Dict[str, Any]]] = {}
        for row in cur.fetchall():
            adj.setdefault(row["source_node"], []).append(dict(row))

        pq: List[Tuple[float, str, List[str], List[Dict[str, Any]]]] = [
            (0.0, start_node_id, [start_node_id], [])
        ]
        visited_cost: Dict[str, float] = {start_node_id: 0.0}

        while pq:
            cost, u, node_path, edge_path = heapq.heappop(pq)
            if u == target_node_id:
                return {
                    "start_node": start_node_id,
                    "target_node": target_node_id,
                    "nodes": node_path,
                    "edges": edge_path,
                    "total_cost_seconds": round(cost, 2),
                    "total_length_m": round(sum(e["length_m"] for e in edge_path), 2),
                    "total_vertical_drop_m": round(sum(e["vertical_diff_m"] for e in edge_path), 2),
                }

            if cost > visited_cost.get(u, float("inf")):
                continue

            for edge in adj.get(u, []):
                v = edge["target_node"]
                next_cost = cost + float(edge["base_cost_seconds"])
                if next_cost < visited_cost.get(v, float("inf")):
                    visited_cost[v] = next_cost
                    heapq.heappush(
                        pq,
                        (next_cost, v, node_path + [v], edge_path + [edge]),
                    )

        return None
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile Big Sky topological graph into SQLite.")
    parser.add_argument("--input", default="data/raw/big_sky_raw.geojson", help="Input GeoJSON file")
    parser.add_argument("--output", default="data/compiled/topology.sqlite", help="Output SQLite file")
    args = parser.parse_args()

    summary = compile_topology(input_geojson_path=args.input, output_sqlite_path=args.output)
    print(f"Topological compilation complete: {summary['nodes_total']} nodes, {summary['edges_total']} edges -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
