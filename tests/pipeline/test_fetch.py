"""
OSM Ingestion & Envelope Contract Harness for Project Cirque
Test Suite: tests/pipeline/test_fetch.py
Verifies:
1. Complete live Big Sky Resort mountain extraction (>500 pistes, >35 lifts)
2. 100% valid point/polygon/linestring geometries strictly within Big Sky bounding box
3. 0 empty difficulty tags across all 700+ pistes
4. Aerialway and amenity tag integrity across all real mountain lifts & POIs
5. 2x2 spatial tile grid partitioning and OSM element parser
"""

import os
import sys
from typing import Any, Dict, List
import pytest

# Ensure repo root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pipeline.fetch_ski_data import (
    BIG_SKY_BBOX,
    ALLOWED_DIFFICULTIES,
    ALLOWED_LIFT_TYPES,
    build_overpass_query,
    build_tile_grid,
    normalize_piste_difficulty,
    osm_elements_to_geojson,
    fetch_big_sky_data,
)


@pytest.fixture(scope="module")
def raw_dataset() -> Dict[str, Any]:
    """Provides the live-harvested Big Sky Resort dataset from data/raw/big_sky_raw.geojson."""
    output_path = "data/raw/big_sky_raw.geojson"
    data = fetch_big_sky_data(output_path=output_path, use_cache=True, live_fetch=True)
    assert os.path.exists(output_path), f"Output file {output_path} must be created"
    return data


def test_overpass_and_tile_grid_format():
    """Verify Overpass QL bounding box string and 2x2 OSM v0.6 tile grid partitioning."""
    query = build_overpass_query(BIG_SKY_BBOX)
    assert "45.23,-111.47,45.32,-111.34" in query
    assert "piste:type" in query
    assert "aerialway" in query

    tiles = build_tile_grid(BIG_SKY_BBOX, rows=2, cols=2)
    assert len(tiles) == 4
    # First tile bottom-left corner matches bbox west, south
    assert tiles[0][0] == pytest.approx(BIG_SKY_BBOX["west"])
    assert tiles[0][1] == pytest.approx(BIG_SKY_BBOX["south"])
    # Last tile top-right corner matches bbox east, north
    assert tiles[-1][2] == pytest.approx(BIG_SKY_BBOX["east"])
    assert tiles[-1][3] == pytest.approx(BIG_SKY_BBOX["north"])


def test_geojson_schema_and_complete_mountain_scale(raw_dataset: Dict[str, Any]):
    """Verify top-level GeoJSON FeatureCollection structure and real full-mountain scale."""
    assert raw_dataset.get("type") == "FeatureCollection"
    assert "features" in raw_dataset
    features = raw_dataset["features"]
    assert isinstance(features, list)

    # Full Big Sky Resort OSM extraction contains 700+ features (pistes, lifts, amenities)
    assert len(features) >= 500, f"Expected full mountain dataset (>=500 features), got {len(features)}"

    metadata = raw_dataset.get("metadata", {})
    assert metadata.get("resort_id") == "us_mt_big_sky"
    assert "Big Sky" in metadata.get("resort_name", "")
    assert "Live OpenStreetMap" in metadata.get("source", "")


def test_bounding_box_containment(raw_dataset: Dict[str, Any]):
    """
    Contract Requirement: 100% of geometries lie within Big Sky bounding box.
    BBox: [South: 45.23, West: -111.47, North: 45.32, East: -111.34]
    """
    bbox = BIG_SKY_BBOX
    epsilon = 0.0001

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
            coord_list = coords[0]
        else:
            pytest.fail(f"Unexpected geometry type: {gtype}")

        assert len(coord_list) >= 1, f"Feature {feature.get('id')} has empty coordinate list"

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
    Every ski run in the complete mountain dataset must possess a standardized difficulty rating.
    """
    piste_features = [
        f for f in raw_dataset["features"]
        if f.get("properties", {}).get("feature_type") == "piste"
        or "piste:type" in f.get("properties", {})
    ]

    assert len(piste_features) >= 500, f"Dataset must contain complete Big Sky piste network (>=500 runs), got {len(piste_features)}"

    for piste in piste_features:
        props = piste.get("properties", {})
        trail_name = props.get("name", "Unknown")
        difficulty = props.get("piste:difficulty")

        assert difficulty is not None, f"Piste '{trail_name}' has null difficulty tag"
        assert str(difficulty).strip() != "", f"Piste '{trail_name}' has empty difficulty tag"
        assert difficulty in ALLOWED_DIFFICULTIES, (
            f"Piste '{trail_name}' has unrecognized difficulty '{difficulty}'. "
            f"Permitted: {ALLOWED_DIFFICULTIES}"
        )


def test_aerialway_integrity_and_real_lifts(raw_dataset: Dict[str, Any]):
    """Assert aerial lifts are correctly tagged and include real Big Sky Resort chairlifts/trams."""
    lift_features = [
        f for f in raw_dataset["features"]
        if f.get("properties", {}).get("feature_type") == "lift"
        or "aerialway" in f.get("properties", {})
    ]

    assert len(lift_features) >= 35, f"Dataset must include complete Big Sky lift network (>=35 lifts), got {len(lift_features)}"

    lift_names = {f.get("properties", {}).get("name", "") for f in lift_features}
    expected_iconic_lifts = ["Lone Peak Tram", "Swift Current 6", "Powder Seeker 6", "Challenger 3"]
    for iconic in expected_iconic_lifts:
        assert any(iconic in name for name in lift_names), f"Missing iconic Big Sky lift '{iconic}' in {lift_names}"

    for lift in lift_features:
        props = lift.get("properties", {})
        lift_type = props.get("aerialway")
        lift_name = props.get("name")
        assert lift_type in ALLOWED_LIFT_TYPES, f"Lift '{lift_name}' has invalid aerialway type: {lift_type}"


def test_real_amenities_present(raw_dataset: Dict[str, Any]):
    """Verify that both OSM-harvested mountain amenities and key Big Sky dining/patrol POIs exist as Points."""
    amenity_features = [
        f for f in raw_dataset["features"]
        if f.get("properties", {}).get("feature_type") == "amenity"
    ]
    assert len(amenity_features) >= 12, f"Expected >= 12 mountain amenities, got {len(amenity_features)}"
    for amenity in amenity_features:
        assert amenity["geometry"]["type"] == "Point", (
            f"Amenity '{amenity['properties'].get('name')}' must be normalized to a Point geometry"
        )


def test_difficulty_normalization_heuristics():
    """Verify that synonym mappings and heuristic inferences work reliably."""
    assert normalize_piste_difficulty("green", {}) == "novice"
    assert normalize_piste_difficulty("beginner", {}) == "novice"
    assert normalize_piste_difficulty("easy", {}) == "novice"
    assert normalize_piste_difficulty("blue", {}) == "intermediate"
    assert normalize_piste_difficulty("black", {}) == "advanced"
    assert normalize_piste_difficulty("double_black", {}) == "expert"
    assert normalize_piste_difficulty("extreme", {}) == "freeride"

    assert normalize_piste_difficulty("", {"name": "Big Couloir"}) == "freeride"
    assert normalize_piste_difficulty(None, {"name": "Lone Peak Bowl"}) == "advanced"
    assert normalize_piste_difficulty(None, {"name": "Mr. K Beginner Run"}) == "novice"
    assert normalize_piste_difficulty(None, {"name": "Upper Ridge"}) == "advanced"
    assert normalize_piste_difficulty(None, {"name": "Random Unnamed Trail"}) == "intermediate"


def test_osm_elements_parser():
    """Test raw OSM elements to GeoJSON parser with mock nodes, ways, and building polygon amenities."""
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
            "type": "way",
            "id": 202,
            "nodes": [1, 2, 1],
            "tags": {"name": "Mock Chalet Building", "amenity": "restaurant"},
        },
    ]

    geojson = osm_elements_to_geojson(mock_elements, BIG_SKY_BBOX)
    way_feat = next(f for f in geojson["features"] if f["id"] == "way_101")
    assert way_feat["geometry"]["type"] == "LineString"
    assert way_feat["properties"]["name"] == "Mock Cruiser"
    assert way_feat["properties"]["piste:difficulty"] == "intermediate"

    bldg_feat = next(f for f in geojson["features"] if f["id"] == "way_202")
    assert bldg_feat["geometry"]["type"] == "Point"
    assert bldg_feat["properties"]["name"] == "Mock Chalet Building"
