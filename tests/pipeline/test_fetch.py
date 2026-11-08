"""
OSM Ingestion & Envelope Contract Harness for Project Cirque
Test Suite: tests/pipeline/test_fetch.py
Verifies:
1. 100% valid polygon/linestring geometries within Big Sky bounding box
2. 0 empty difficulty tags on pistes
3. Aerialway and amenity tag integrity
4. Offline canonical fallback and Overpass query parser
"""

import json
import os
import sys
from typing import Any, Dict, List
import pytest

# Ensure repo root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pipeline.fetch_ski_data import (
    BIG_SKY_BBOX,
    ALLOWED_DIFFICULTIES,
    build_overpass_query,
    is_coord_in_bbox,
    normalize_piste_difficulty,
    osm_elements_to_geojson,
    generate_canonical_big_sky_reference,
    fetch_big_sky_data,
)


@pytest.fixture(scope="module")
def raw_dataset() -> Dict[str, Any]:
    """Provides a fresh or cached dataset from data/raw/big_sky_raw.geojson."""
    output_path = "data/raw/big_sky_raw.geojson"
    data = fetch_big_sky_data(output_path=output_path, use_cache=True, live_fetch=False)
    assert os.path.exists(output_path), f"Output file {output_path} must be created"
    return data


def test_overpass_query_format():
    """Verify that Overpass QL bounding box string is formatted correctly: south,west,north,east."""
    query = build_overpass_query(BIG_SKY_BBOX)
    assert "45.23,-111.47,45.32,-111.34" in query
    assert "piste:type" in query
    assert "aerialway" in query
    assert "emergency" in query


def test_geojson_schema_structure(raw_dataset: Dict[str, Any]):
    """Verify top-level GeoJSON FeatureCollection structure and metadata."""
    assert raw_dataset.get("type") == "FeatureCollection"
    assert "features" in raw_dataset
    assert isinstance(raw_dataset["features"], list)
    assert len(raw_dataset["features"]) > 0

    metadata = raw_dataset.get("metadata", {})
    assert metadata.get("resort_id") == "us_mt_big_sky"
    assert "Big Sky" in metadata.get("resort_name", "")


def test_bounding_box_containment(raw_dataset: Dict[str, Any]):
    """
    Contract Requirement: 100% of geometries lie within Big Sky bounding box.
    BBox: [South: 45.23, West: -111.47, North: 45.32, East: -111.34]
    """
    bbox = BIG_SKY_BBOX
    epsilon = 0.005  # Small buffer allowance for summit/ridge boundaries

    for feature in raw_dataset["features"]:
        geom = feature.get("geometry", {})
        gtype = geom.get("type")
        coords = geom.get("coordinates")

        coord_list: List[List[float]] = []
        if gtype == "Point":
            coord_list = [coords]
        elif gtype == "LineString":
            coord_list = coords
        elif gtype == "Polygon":
            # Outer ring
            coord_list = coords[0]
        else:
            pytest.fail(f"Unexpected geometry type: {gtype}")

        for lon, lat in coord_list:
            in_bounds = (
                (bbox["west"] - epsilon) <= lon <= (bbox["east"] + epsilon)
                and (bbox["south"] - epsilon) <= lat <= (bbox["north"] + epsilon)
            )
            assert in_bounds, (
                f"Coordinate ({lon}, {lat}) in feature '{feature.get('properties', {}).get('name')}' "
                f"exceeds bounding box {bbox}"
            )


def test_zero_empty_difficulty_tags(raw_dataset: Dict[str, Any]):
    """
    Pass Criteria: 0 empty difficulty tags on pistes.
    Every ski run must possess a standardized difficulty rating.
    """
    piste_features = [
        f for f in raw_dataset["features"]
        if f.get("properties", {}).get("feature_type") == "piste"
        or "piste:type" in f.get("properties", {})
    ]

    assert len(piste_features) > 0, "Dataset must contain piste features"

    for piste in piste_features:
        props = piste.get("properties", {})
        trail_name = props.get("name", "Unknown")
        difficulty = props.get("piste:difficulty")

        # Must not be None, empty string, or whitespace
        assert difficulty is not None, f"Piste '{trail_name}' has null difficulty tag"
        assert str(difficulty).strip() != "", f"Piste '{trail_name}' has empty difficulty tag"

        # Must be in authorized vocabulary
        assert difficulty in ALLOWED_DIFFICULTIES, (
            f"Piste '{trail_name}' has unrecognized difficulty '{difficulty}'. "
            f"Permitted: {ALLOWED_DIFFICULTIES}"
        )


def test_aerialway_integrity(raw_dataset: Dict[str, Any]):
    """Assert aerial lifts are correctly tagged with valid aerialway types."""
    lift_features = [
        f for f in raw_dataset["features"]
        if f.get("properties", {}).get("feature_type") == "lift"
        or "aerialway" in f.get("properties", {})
    ]

    assert len(lift_features) >= 5, "Dataset must include primary Big Sky lifts"

    allowed_lift_types = {"chair_lift", "cable_car", "gondola", "t-bar", "platter", "magic_carpet"}
    for lift in lift_features:
        props = lift.get("properties", {})
        lift_type = props.get("aerialway")
        lift_name = props.get("name")
        assert lift_type in allowed_lift_types, f"Lift '{lift_name}' has invalid aerialway type: {lift_type}"


def test_difficulty_normalization_heuristics():
    """Verify that synonym mappings and heuristic inferences work reliably."""
    assert normalize_piste_difficulty("green", {}) == "novice"
    assert normalize_piste_difficulty("beginner", {}) == "novice"
    assert normalize_piste_difficulty("blue", {}) == "intermediate"
    assert normalize_piste_difficulty("black", {}) == "advanced"
    assert normalize_piste_difficulty("double_black", {}) == "expert"
    assert normalize_piste_difficulty("extreme", {}) == "freeride"

    # Inferences when raw tag is absent or empty
    assert normalize_piste_difficulty("", {"name": "Big Couloir"}) == "freeride"
    assert normalize_piste_difficulty(None, {"name": "Lone Peak Bowl"}) == "advanced"
    assert normalize_piste_difficulty(None, {"name": "Mr. K Beginner Run"}) == "novice"
    assert normalize_piste_difficulty(None, {"name": "Upper Ridge"}) == "advanced"
    assert normalize_piste_difficulty(None, {"name": "Random Unnamed Trail"}) == "intermediate"


def test_osm_elements_parser():
    """Test raw OSM elements to GeoJSON parser with mock nodes and ways."""
    mock_elements = [
        {"type": "node", "id": 1, "lat": 45.2800, "lon": -111.4100},
        {"type": "node", "id": 2, "lat": 45.2850, "lon": -111.4050},
        {
            "type": "way",
            "id": 101,
            "nodes": [1, 2],
            "tags": {
                "name": "Mock Cruiser",
                "piste:type": "downhill",
                "piste:difficulty": "intermediate",
            },
        },
        {
            "type": "node",
            "id": 3,
            "lat": 45.2750,
            "lon": -111.4120,
            "tags": {"name": "Mock Patrol Hut", "amenity": "shelter", "emergency": "first_aid"},
        },
    ]

    geojson = osm_elements_to_geojson(mock_elements, BIG_SKY_BBOX)
    assert len(geojson["features"]) == 2

    way_feat = next(f for f in geojson["features"] if f["id"] == "way_101")
    assert way_feat["geometry"]["type"] == "LineString"
    assert way_feat["properties"]["name"] == "Mock Cruiser"
    assert way_feat["properties"]["piste:difficulty"] == "intermediate"

    node_feat = next(f for f in geojson["features"] if f["id"] == "node_3")
    assert node_feat["geometry"]["type"] == "Point"
    assert node_feat["properties"]["name"] == "Mock Patrol Hut"
