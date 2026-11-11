"""
OSM Ingestion & Envelope Contract Harness for Project Cirque.
Test Suite: tests/pipeline/test_fetch.py
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import pytest

from pipeline.fetch_ski_data import (
    ALLOWED_AERIALWAYS,
    ALLOWED_DIFFICULTIES,
    BIG_SKY_BBOX,
    build_fast_overpass_query,
    fetch_big_sky_data,
    normalize_difficulty,
    parse_geom_elements_to_geojson,
)


@pytest.fixture(scope="module")
def raw_dataset() -> Dict[str, Any]:
    output_path = "data/raw/big_sky_raw.geojson"
    assert os.path.exists(output_path), f"Cached GeoJSON dataset missing at {output_path}"
    return fetch_big_sky_data(output_path=output_path, use_cache=True, live_fetch=False)


def test_overpass_query_format():
    query = build_fast_overpass_query(BIG_SKY_BBOX)
    expected_bbox = (
        f"{BIG_SKY_BBOX['south']},{BIG_SKY_BBOX['west']},"
        f"{BIG_SKY_BBOX['north']},{BIG_SKY_BBOX['east']}"
    )
    assert expected_bbox in query
    assert "piste:type" in query
    assert "aerialway" in query
    assert "out geom;" in query


def test_geojson_schema_and_complete_mountain_scale(raw_dataset: Dict[str, Any]):
    assert raw_dataset.get("type") == "FeatureCollection"
    features = raw_dataset.get("features")
    assert isinstance(features, list)
    assert len(features) >= 500, f"Expected full mountain dataset (>=500 features), got {len(features)}"
    assert "Big Sky" in raw_dataset.get("resort", "")


def test_bounding_box_containment(raw_dataset: Dict[str, Any]):
    epsilon = 0.001
    for feature in raw_dataset["features"]:
        geom = feature.get("geometry", {})
        gtype = geom.get("type")
        coords = geom.get("coordinates")

        if gtype == "Point":
            coord_list: List[List[float]] = [coords]
        elif gtype == "LineString":
            coord_list = coords
        elif gtype == "Polygon":
            coord_list = coords[0]
        else:
            pytest.fail(f"Unexpected geometry type: {gtype}")

        assert len(coord_list) >= 1, f"Feature {feature.get('id')} has empty coordinate list"
        for lon, lat in coord_list:
            in_bounds = (
                (BIG_SKY_BBOX["west"] - epsilon) <= lon <= (BIG_SKY_BBOX["east"] + epsilon)
                and (BIG_SKY_BBOX["south"] - epsilon) <= lat <= (BIG_SKY_BBOX["north"] + epsilon)
            )
            assert in_bounds, (
                f"Coordinate ({lon}, {lat}) in '{feature.get('properties', {}).get('name')}' "
                f"exceeds bounding box {BIG_SKY_BBOX}"
            )


def test_zero_empty_difficulty_tags(raw_dataset: Dict[str, Any]):
    piste_features = [
        f for f in raw_dataset["features"]
        if f.get("properties", {}).get("type") == "piste"
    ]
    assert len(piste_features) >= 500, f"Expected >=500 pistes, got {len(piste_features)}"

    for piste in piste_features:
        props = piste.get("properties", {})
        trail_name = props.get("name", "Unknown")
        difficulty = props.get("difficulty")

        assert difficulty is not None, f"Piste '{trail_name}' has null difficulty tag"
        assert difficulty.strip() != "", f"Piste '{trail_name}' has empty difficulty tag"
        assert difficulty in ALLOWED_DIFFICULTIES, (
            f"Piste '{trail_name}' has unrecognized difficulty '{difficulty}'."
        )


def test_aerialway_integrity_and_real_lifts(raw_dataset: Dict[str, Any]):
    lift_features = [
        f for f in raw_dataset["features"]
        if f.get("properties", {}).get("type") == "lift"
    ]
    assert len(lift_features) >= 35, f"Expected >=35 lifts, got {len(lift_features)}"

    lift_names = {f.get("properties", {}).get("name", "") for f in lift_features}
    for iconic in ("Lone Peak Tram", "Swift Current 6", "Powder Seeker 6", "Challenger 3"):
        assert any(iconic in name for name in lift_names), f"Missing iconic lift '{iconic}'"

    for lift in lift_features:
        props = lift.get("properties", {})
        assert props.get("subtype") in ALLOWED_AERIALWAYS
        assert props.get("difficulty") == "lift"


def test_difficulty_normalization_heuristics():
    assert normalize_difficulty("green") == "novice"
    assert normalize_difficulty("beginner") == "novice"
    assert normalize_difficulty("easy") == "novice"
    assert normalize_difficulty("blue") == "intermediate"
    assert normalize_difficulty("black") == "advanced"
    assert normalize_difficulty("double_black") == "expert"
    assert normalize_difficulty("extreme") == "freeride"

    assert normalize_difficulty("", {"name": "Big Couloir"}) == "freeride"
    assert normalize_difficulty(None, {"name": "Lone Peak Bowl"}) == "advanced"
    assert normalize_difficulty(None, {"name": "Mr. K Beginner Run"}) == "novice"
    assert normalize_difficulty(None, {"name": "Upper Ridge"}) == "advanced"
    assert normalize_difficulty(None, {"name": "Random Unnamed Trail"}) == "intermediate"


def test_parse_geom_elements_to_geojson():
    mock_osm = {
        "elements": [
            {
                "type": "way",
                "id": 101,
                "tags": {
                    "name": "Mock Cruiser",
                    "piste:type": "downhill",
                    "piste:difficulty": "intermediate",
                    "piste:grooming": "classic",
                },
                "geometry": [
                    {"lat": 45.2800, "lon": -111.4100},
                    {"lat": 45.2850, "lon": -111.4050},
                ],
            },
            {
                "type": "way",
                "id": 202,
                "tags": {"highway": "residential", "name": "Mountain Loop Rd"},
                "geometry": [
                    {"lat": 45.2840, "lon": -111.4010},
                    {"lat": 45.2845, "lon": -111.4005},
                ],
            },
            {
                "type": "relation",
                "id": 900,
                "tags": {
                    "route": "piste",
                    "name": "Liberty Bowl",
                    "piste:difficulty": "advanced",
                    "piste:type": "downhill",
                },
                "members": [
                    {
                        "type": "way",
                        "ref": 303,
                        "geometry": [
                            {"lat": 45.2785, "lon": -111.4510},
                            {"lat": 45.2715, "lon": -111.4450},
                        ],
                    }
                ],
            },
        ]
    }

    geojson = parse_geom_elements_to_geojson(mock_osm, BIG_SKY_BBOX)
    assert len(geojson["features"]) == 2
    ids = {f["id"] for f in geojson["features"]}
    assert "osm_way_202" not in ids

    cruiser = next(f for f in geojson["features"] if f["id"] == "osm_way_101")
    assert cruiser["geometry"]["type"] == "LineString"
    assert cruiser["properties"]["name"] == "Mock Cruiser"
    assert cruiser["properties"]["difficulty"] == "intermediate"

    inherited = next(f for f in geojson["features"] if f["id"] == "osm_way_303")
    assert inherited["properties"]["name"] == "Liberty Bowl"
    assert inherited["properties"]["difficulty"] == "advanced"
