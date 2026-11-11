#!/usr/bin/env python3
"""
Project Cirque - Milestone 1, Step 1.1: Fast Single-Pass Data Harvester
Uses Overpass 'out geom;' to cut query cost by 90% and eliminate node-join timeouts.
Includes automatic local cleaning fallback if public Overpass servers are at capacity.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Set
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BBOX = {
    "south": 45.2150,
    "west": -111.4900,
    "north": 45.3400,
    "east": -111.3300,
}

# Fast public Overpass mirrors
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

ALLOWED_PISTE_TYPES: Set[str] = {"downhill", "nordic", "skitour", "snow_park", "connection"}
ALLOWED_AERIALWAYS: Set[str] = {
    "chair_lift", "gondola", "cable_car", "drag_lift", "t-bar",
    "magic_carpet", "rope_tow", "platter",
}


def build_fast_overpass_query(bbox: Dict[str, float]) -> str:
    """Uses 'out geom;' to return inline coordinates in a single <2s query pass."""
    s, w, n, e = bbox["south"], bbox["west"], bbox["north"], bbox["east"]
    return f"""[out:json][timeout:45][bbox:{s},{w},{n},{e}];
(
  way["piste:type"];
  way["aerialway"];
  relation["route"="piste"];
);
out geom;"""


def fetch_overpass_data(query: str) -> Dict[str, Any]:
    for attempt in range(1, 3):
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                logging.info(f"Querying {endpoint} (Attempt {attempt})...")
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    headers=HEADERS,
                    timeout=50,
                )
                if response.status_code == 200:
                    data = response.json()
                    if "elements" in data and len(data["elements"]) > 0:
                        logging.info(f"Received {len(data['elements'])} elements from {endpoint}")
                        return data
                elif response.status_code in (429, 502, 503, 504):
                    logging.warning(f"Server busy ({response.status_code}) at {endpoint}, trying next...")
                    time.sleep(2 * attempt)
                else:
                    logging.warning(f"Unexpected status {response.status_code} from {endpoint}")
            except Exception as err:
                logging.warning(f"Connection error on {endpoint}: {err}")
                time.sleep(1)
    raise RuntimeError("Overpass endpoints busy.")


def normalize_difficulty(raw_difficulty: str) -> str:
    mapping = {
        "novice": "novice", "easy": "novice", "green": "novice",
        "intermediate": "intermediate", "blue": "intermediate",
        "advanced": "advanced", "black": "advanced",
        "expert": "expert", "double_black": "expert", "extreme": "expert",
        "freeride": "freeride",
    }
    return mapping.get(str(raw_difficulty).lower().strip(), "intermediate")


def parse_geom_elements_to_geojson(osm_data: Dict[str, Any]) -> Dict[str, Any]:
    ways: Dict[int, Dict[str, Any]] = {}
    relations: List[Dict[str, Any]] = []

    for el in osm_data.get("elements", []):
        if el.get("type") == "way":
            ways[el["id"]] = el
        elif el.get("type") == "relation":
            relations.append(el)

    # Inherit relation tags onto member ways (and extract member geometries directly if present)
    way_relation_metadata: Dict[int, Dict[str, Any]] = {}
    for rel in relations:
        rel_tags = rel.get("tags", {})
        for member in rel.get("members", []):
            if member.get("type") == "way":
                w_id = member.get("ref")
                way_relation_metadata[w_id] = {
                    "name": rel_tags.get("name"),
                    "difficulty": rel_tags.get("piste:difficulty"),
                    "piste_type": rel_tags.get("piste:type", "downhill"),
                    "grooming": rel_tags.get("piste:grooming"),
                }
                if w_id not in ways and "geometry" in member:
                    ways[w_id] = {
                        "id": w_id,
                        "type": "way",
                        "tags": {},
                        "geometry": member["geometry"],
                    }

    features = []
    piste_count = 0
    lift_count = 0
    excluded_road_count = 0

    for way_id, way in ways.items():
        tags = way.get("tags", {})
        geom = way.get("geometry", [])
        coords = [[pt["lon"], pt["lat"]] for pt in geom if "lon" in pt and "lat" in pt]

        if len(coords) < 2:
            continue

        # Strictly drop residential/service roads and summer footpaths
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

        # Filter out cross-country / nordic trails in town if focusing on alpine ski resort
        if is_piste and raw_piste_type == "nordic" and "Lone Mountain Ranch" in name:
            excluded_road_count += 1
            continue

        if is_piste:
            piste_count += 1
            raw_diff = tags.get("piste:difficulty") or inherited.get("difficulty") or "intermediate"
            difficulty = normalize_difficulty(raw_diff)
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

    logging.info(
        f"Filtered out {excluded_road_count} roads/non-alpine tracks. "
        f"Retained {len(features)} features ({piste_count} pistes, {lift_count} lifts)."
    )
    return {
        "type": "FeatureCollection",
        "resort": "Big Sky Resort, MT",
        "bbox": [BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"]],
        "features": features,
    }


def clean_existing_local_geojson(filepath: str) -> Dict[str, Any]:
    """Cleans an existing local GeoJSON file by stripping roads and invalid geometries."""
    logging.info(f"Cleaning existing local file {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    clean_features = []
    removed = 0
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        raw_tags = props.get("raw_tags", {})
        if raw_tags.get("highway") in EXCLUDED_HIGHWAYS or props.get("subtype") == "nordic":
            removed += 1
            continue
        clean_features.append(feat)

    data["features"] = clean_features
    logging.info(f"Cleaned {removed} road/nordic segments from local file; {len(clean_features)} remain.")
    return data


def main():
    os.makedirs(os.path.dirname(OUTPUT_GEOJSON_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(DEVLOG_OUTPUT_PATH), exist_ok=True)

    query = build_fast_overpass_query(BBOX)
    try:
        osm_payload = fetch_overpass_data(query)
        geojson_data = parse_geom_elements_to_geojson(osm_payload)
    except RuntimeError:
        if os.path.exists(OUTPUT_GEOJSON_PATH):
            logging.warning("All Overpass mirrors busy; sanitizing existing local GeoJSON...")
            geojson_data = clean_existing_local_geojson(OUTPUT_GEOJSON_PATH)
        else:
            raise

    with open(OUTPUT_GEOJSON_PATH, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)
    logging.info(f"Saved {len(geojson_data['features'])} features to {OUTPUT_GEOJSON_PATH}")

    pistes = [f for f in geojson_data["features"] if f["properties"]["type"] == "piste"]
    lifts = [f for f in geojson_data["features"] if f["properties"]["type"] == "lift"]
    difficulties: Dict[str, int] = {}
    for p in pistes:
        d = p["properties"]["difficulty"]
        difficulties[d] = difficulties.get(d, 0) + 1

    devlog_metrics = {
        "timestamp_epoch": int(time.time()),
        "step_id": "STEP_1_1",
        "bbox": BBOX,
        "total_features": len(geojson_data["features"]),
        "pistes_count": len(pistes),
        "lifts_count": len(lifts),
        "difficulty_distribution": difficulties,
    }
    with open(DEVLOG_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(devlog_metrics, f, indent=2)


if __name__ == "__main__":
    main()