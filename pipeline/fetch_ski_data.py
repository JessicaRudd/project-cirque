#!/usr/bin/env python3
"""
Project Cirque - Milestone 1, Step 1.1: Single-Pass OSM Overpass Data Harvester.
Uses Overpass 'out geom;' to return inline LineString coordinates for Big Sky pistes and lifts.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Set

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cirque_fetch")

# Covers Lone Peak, Andesite, Moonlight Basin, and Spanish Peaks interconnected lift network
BIG_SKY_BBOX: Dict[str, float] = {
    "south": 45.2050,
    "west": -111.4900,
    "north": 45.3400,
    "east": -111.3150,
}

OVERPASS_ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

HEADERS = {
    "User-Agent": "ProjectCirque/1.1 (https://github.com/JessicaRudd/project-cirque)",
    "Accept": "application/json",
}

OUTPUT_GEOJSON_PATH = "data/raw/big_sky_raw.geojson"
DEVLOG_OUTPUT_PATH = ".cirque/devlog/M1_DATA_PLANE/step_1_1.json"

EXCLUDED_HIGHWAYS: Set[str] = {
    "residential", "service", "primary", "secondary", "tertiary",
    "unclassified", "motorway", "trunk", "living_street", "parking_aisle",
    "track", "footway", "path", "steps", "pedestrian", "cycleway",
}

ALLOWED_DIFFICULTIES: Set[str] = {"novice", "intermediate", "advanced", "expert", "freeride"}
ALLOWED_PISTE_TYPES: Set[str] = {"downhill", "nordic", "skitour", "snow_park", "connection"}
ALLOWED_AERIALWAYS: Set[str] = {
    "chair_lift", "gondola", "cable_car", "drag_lift", "t-bar",
    "magic_carpet", "rope_tow", "platter",
}


def build_fast_overpass_query(bbox: Dict[str, float]) -> str:
    """Uses 'out geom;' to return inline way and relation geometries in a single query pass."""
    s, w, n, e = bbox["south"], bbox["west"], bbox["north"], bbox["east"]
    return f"""[out:json][timeout:45][bbox:{s},{w},{n},{e}];
(
  way["piste:type"];
  way["aerialway"];
  relation["route"="piste"];
);
out geom;"""


def fetch_overpass_data(query: str) -> Dict[str, Any]:
    encoded = urllib.parse.urlencode({"data": query}).encode("utf-8")
    for attempt in range(1, 3):
        for endpoint in OVERPASS_ENDPOINTS:
            req = urllib.request.Request(endpoint, data=encoded, headers=HEADERS, method="POST")
            try:
                logger.info("Querying %s (attempt %d)...", endpoint, attempt)
                with urllib.request.urlopen(req, timeout=50) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        if data.get("elements"):
                            logger.info("Received %d elements from %s", len(data["elements"]), endpoint)
                            return data
            except urllib.error.HTTPError as err:
                if err.code in (429, 502, 503, 504):
                    logger.warning("Server busy (%d) at %s, trying next...", err.code, endpoint)
                    time.sleep(2 * attempt)
                else:
                    raise
            except (urllib.error.URLError, TimeoutError, ValueError) as err:
                logger.warning("Overpass request failed on %s: %s", endpoint, err)
                time.sleep(1)
    raise RuntimeError("All Overpass mirrors timed out or returned empty payloads.")


def normalize_difficulty(
    raw_difficulty: Optional[str],
    tags: Optional[Dict[str, Any]] = None,
) -> str:
    mapping = {
        "novice": "novice",
        "beginner": "novice",
        "easy": "novice",
        "green": "novice",
        "intermediate": "intermediate",
        "blue": "intermediate",
        "advanced": "advanced",
        "black": "advanced",
        "expert": "expert",
        "double_black": "expert",
        "freeride": "freeride",
        "extreme": "freeride",
    }
    if raw_difficulty:
        normalized = raw_difficulty.lower().strip()
        if normalized in mapping:
            return mapping[normalized]

    name_lower = ((tags or {}).get("name") or "").lower()
    if any(tok in name_lower for tok in ("couloir", "chute", "dictator", "headwaters")):
        return "freeride"
    if any(tok in name_lower for tok in ("bowl", "gully", "gullies", "ridge", "cliff")):
        return "advanced"
    if any(tok in name_lower for tok in ("beginner", "learning", "meadow", "mr. k", "carpet")):
        return "novice"
    return "intermediate"


def parse_geom_elements_to_geojson(
    osm_data: Dict[str, Any],
    bbox: Dict[str, float] = BIG_SKY_BBOX,
) -> Dict[str, Any]:
    ways: Dict[int, Dict[str, Any]] = {}
    relations: List[Dict[str, Any]] = []

    for el in osm_data.get("elements", []):
        if el.get("type") == "way":
            ways[el["id"]] = el
        elif el.get("type") == "relation":
            relations.append(el)

    # Inherit relation tags onto member ways without clobbering already-populated fields across multi-relations
    way_relation_metadata: Dict[int, Dict[str, Any]] = {}
    for rel in relations:
        rel_tags = rel.get("tags", {})
        for member in rel.get("members", []):
            if member.get("type") != "way":
                continue
            w_id = member.get("ref")
            if w_id is None:
                continue
            existing = way_relation_metadata.setdefault(w_id, {})
            for field, tag_key in (
                ("name", "name"),
                ("difficulty", "piste:difficulty"),
                ("piste_type", "piste:type"),
                ("grooming", "piste:grooming"),
            ):
                if not existing.get(field) and rel_tags.get(tag_key):
                    existing[field] = rel_tags[tag_key]
            if not existing.get("piste_type"):
                existing["piste_type"] = "downhill"

            if w_id not in ways and "geometry" in member:
                ways[w_id] = {
                    "id": w_id,
                    "type": "way",
                    "tags": {},
                    "geometry": member["geometry"],
                }

    features: List[Dict[str, Any]] = []
    piste_count = 0
    lift_count = 0
    excluded_road_count = 0

    for way_id, way in ways.items():
        tags = way.get("tags", {})
        geom = way.get("geometry", [])
        coords = [[pt["lon"], pt["lat"]] for pt in geom if "lon" in pt and "lat" in pt]
        if len(coords) < 2:
            continue

        if tags.get("highway") in EXCLUDED_HIGHWAYS or "building" in tags or "landuse" in tags:
            excluded_road_count += 1
            continue

        inherited = way_relation_metadata.get(way_id, {})
        raw_piste_type = tags.get("piste:type") or inherited.get("piste_type")
        raw_aerialway = tags.get("aerialway")

        is_piste = raw_piste_type in ALLOWED_PISTE_TYPES
        is_lift = raw_aerialway in ALLOWED_AERIALWAYS
        if not (is_piste or is_lift):
            continue

        feature_type = "piste" if is_piste else "lift"
        name = tags.get("name") or inherited.get("name") or f"Unnamed {feature_type.capitalize()}"

        # Exclude off-resort town cross-country tracks belonging to Lone Mountain Ranch
        if is_piste and raw_piste_type == "nordic" and "Lone Mountain Ranch" in name:
            excluded_road_count += 1
            continue

        if is_piste:
            piste_count += 1
            raw_diff = tags.get("piste:difficulty") or inherited.get("difficulty")
            difficulty = normalize_difficulty(raw_diff, {"name": name})
            subtype = raw_piste_type
        else:
            lift_count += 1
            difficulty = "lift"
            subtype = raw_aerialway

        features.append({
            "type": "Feature",
            "id": f"osm_way_{way_id}",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "id": str(way_id),
                "name": name,
                "type": feature_type,
                "subtype": subtype,
                "difficulty": difficulty,
                "grooming": tags.get("piste:grooming") or inherited.get("grooming"),
                "oneway": tags.get("oneway", "yes" if is_piste else "no"),
            },
        })

    logger.info(
        "Filtered %d roads/nordic tracks; retained %d features (%d pistes, %d lifts).",
        excluded_road_count,
        len(features),
        piste_count,
        lift_count,
    )
    return {
        "type": "FeatureCollection",
        "resort": "Big Sky Resort, MT",
        "bbox": [bbox["west"], bbox["south"], bbox["east"], bbox["north"]],
        "features": features,
    }


def fetch_big_sky_data(
    output_path: str = OUTPUT_GEOJSON_PATH,
    use_cache: bool = True,
    live_fetch: bool = False,
) -> Dict[str, Any]:
    if use_cache and not live_fetch and os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            return json.load(f)

    query = build_fast_overpass_query(BIG_SKY_BBOX)
    osm_payload = fetch_overpass_data(query)
    geojson_data = parse_geom_elements_to_geojson(osm_payload, BIG_SKY_BBOX)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)
    return geojson_data


def main() -> None:
    geojson_data = fetch_big_sky_data(OUTPUT_GEOJSON_PATH, use_cache=False, live_fetch=True)
    logger.info("Saved %d features to %s", len(geojson_data["features"]), OUTPUT_GEOJSON_PATH)

    pistes = [f for f in geojson_data["features"] if f["properties"]["type"] == "piste"]
    lifts = [f for f in geojson_data["features"] if f["properties"]["type"] == "lift"]
    difficulties: Dict[str, int] = {}
    for p in pistes:
        d = p["properties"]["difficulty"]
        difficulties[d] = difficulties.get(d, 0) + 1

    devlog_metrics = {
        "timestamp_epoch": int(time.time()),
        "step_id": "STEP_1_1",
        "bbox": BIG_SKY_BBOX,
        "total_features": len(geojson_data["features"]),
        "pistes_count": len(pistes),
        "lifts_count": len(lifts),
        "difficulty_distribution": difficulties,
    }
    dev_dir = os.path.dirname(DEVLOG_OUTPUT_PATH)
    if dev_dir:
        os.makedirs(dev_dir, exist_ok=True)
    with open(DEVLOG_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(devlog_metrics, f, indent=2)


if __name__ == "__main__":
    main()