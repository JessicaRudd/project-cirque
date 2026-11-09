"""Unit tests for Gemma SLM Intent Parser & Prompt Contracts.

Tests:
1. Valid JSON schema export and conformance.
2. Pydantic validation success across core skier queries.
3. Invalid enum rejection & fallback defense.
4. Markdown code fence stripping & sanitization.
5. End-to-end mock engine execution.
"""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from slm.gemma_intent_parser import (
    GemmaIntentParser,
    SkiIntent,
    build_gemma_prompt,
    export_intent_json_schema,
    sanitize_model_output,
)


def test_valid_json_schema_export():
    """Asserts that intent_schema.json matches Pydantic's exported schema."""
    schema_path = Path("slm/schemas/intent_schema.json")
    assert schema_path.exists(), "slm/schemas/intent_schema.json must exist"

    disk_schema = json.loads(schema_path.read_text())
    pydantic_schema = export_intent_json_schema()

    assert disk_schema == pydantic_schema
    assert disk_schema["title"] == "SkiIntent"
    assert "properties" in disk_schema
    properties = disk_schema["properties"]

    expected_keys = [
        "target_poi_category",
        "target_poi_name",
        "service_speed",
        "max_difficulty",
        "preferred_grooming",
        "avoid_moguls",
        "must_be_open",
        "avoid_lifts",
    ]
    for key in expected_keys:
        assert key in properties, f"Missing property {key} in JSON schema"


def test_pydantic_validation_success():
    """Validates parsing on typical ski prompts (snack search, powder bowl navigation, ski patrol emergency)."""
    # 1. Quick snack query
    snack_payload = {
        "target_poi_category": "quick_snack",
        "target_poi_name": None,
        "service_speed": "grab_and_go",
        "max_difficulty": "intermediate",
        "preferred_grooming": True,
        "avoid_moguls": False,
        "must_be_open": True,
        "avoid_lifts": ["Swift Current 6"],
    }
    snack_intent = SkiIntent.model_validate(snack_payload)
    assert snack_intent.target_poi_category == "quick_snack"
    assert snack_intent.service_speed == "grab_and_go"
    assert snack_intent.max_difficulty == "intermediate"
    assert snack_intent.preferred_grooming is True
    assert snack_intent.avoid_lifts == ["Swift Current 6"]

    # 2. Powder bowl navigation
    bowl_payload = {
        "target_poi_category": None,
        "target_poi_name": "Liberty Bowl",
        "service_speed": None,
        "max_difficulty": "expert",
        "preferred_grooming": False,
        "avoid_moguls": False,
        "must_be_open": True,
        "avoid_lifts": [],
    }
    bowl_intent = SkiIntent.model_validate(bowl_payload)
    assert bowl_intent.target_poi_name == "Liberty Bowl"
    assert bowl_intent.max_difficulty == "expert"
    assert bowl_intent.preferred_grooming is False

    # 3. Ski patrol emergency
    emergency_payload = {
        "target_poi_category": "patrol",
        "target_poi_name": None,
        "service_speed": None,
        "max_difficulty": "expert",
        "preferred_grooming": False,
        "avoid_moguls": False,
        "must_be_open": True,
        "avoid_lifts": [],
    }
    emergency_intent = SkiIntent.model_validate(emergency_payload)
    assert emergency_intent.target_poi_category == "patrol"
    assert emergency_intent.must_be_open is True


def test_invalid_enum_rejection():
    """Asserts that invalid difficulty values raise validation errors and parser falls back to safe defaults."""
    parser = GemmaIntentParser(mode="mock")

    # Direct Pydantic validation should raise ValidationError on unknown difficulty
    invalid_raw = {
        "target_poi_category": "cafeteria",
        "max_difficulty": "super_hard",  # Invalid!
    }
    with pytest.raises(ValidationError):
        SkiIntent.model_validate(invalid_raw)

    # Invalid POI category should also raise ValidationError
    invalid_category = {
        "target_poi_category": "nightclub",  # Invalid!
    }
    with pytest.raises(ValidationError):
        SkiIntent.model_validate(invalid_category)

    # Parser method parse() gracefully falls back to default safe SkiIntent
    invalid_json_str = json.dumps(invalid_raw)
    fallback_intent = parser.parse(invalid_json_str)
    assert isinstance(fallback_intent, SkiIntent)
    assert fallback_intent.max_difficulty == "advanced"  # default safe fallback
    assert fallback_intent.target_poi_category is None


def test_parser_strips_markdown_fences():
    """Asserts that model responses wrapped in ```json ... ``` are cleanly sanitized and parsed."""
    parser = GemmaIntentParser(mode="mock")

    wrapped_response = """```json
{
  "target_poi_category": "sit_down",
  "target_poi_name": "Everett's 8800",
  "service_speed": "table_service",
  "max_difficulty": "intermediate",
  "preferred_grooming": true,
  "avoid_moguls": true,
  "must_be_open": true,
  "avoid_lifts": []
}
```"""

    intent = parser.parse(wrapped_response)
    assert intent.target_poi_category == "sit_down"
    assert intent.target_poi_name == "Everett's 8800"
    assert intent.service_speed == "table_service"
    assert intent.max_difficulty == "intermediate"
    assert intent.avoid_moguls is True

    # Test conversational framing around json block
    conversational_response = """Sure! Here is the JSON you requested:
```
{
  "target_poi_category": "warming_hut",
  "max_difficulty": "novice",
  "must_be_open": true
}
```
Hope that helps!"""

    intent2 = parser.parse(conversational_response)
    assert intent2.target_poi_category == "warming_hut"
    assert intent2.max_difficulty == "novice"


def test_mock_engine_end_to_end():
    """Asserts that the parser runs end-to-end in mock mode without external dependencies."""
    parser = GemmaIntentParser(mode="mock")

    # 1. Emergency query
    intent1 = parser.process_transcript("Emergency! Ski patrol needed on Swift Current!")
    assert intent1.target_poi_category == "patrol"
    assert intent1.max_difficulty == "expert"

    # 2. Sit-down lunch query
    intent2 = parser.process_transcript("Find me a sit down lunch on blue groomed cruisers with no moguls")
    assert intent2.target_poi_category == "sit_down"
    assert intent2.max_difficulty == "intermediate"
    assert intent2.preferred_grooming is True
    assert intent2.avoid_moguls is True

    # 3. Quick snack query
    intent3 = parser.process_transcript("I need a quick burger or snack for intermediate skier")
    assert intent3.target_poi_category == "quick_snack"
    assert intent3.service_speed == "grab_and_go"
    assert intent3.max_difficulty == "intermediate"

    # 4. Prompt construction check
    prompt = build_gemma_prompt(
        transcript="Find me a warm lunch",
        current_node_id="node_swift_current_top",
        current_time_local="12:30",
    )
    assert "node_swift_current_top" in prompt
    assert "12:30" in prompt
    assert "Find me a warm lunch" in prompt
    assert "You are the Cirque On-Device Ski Routing Engine." in prompt
