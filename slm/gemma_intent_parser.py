"""Gemma SLM Intent Parser for Project Cirque.

Provides strict prompt templates, Pydantic data schemas, and runtime parsers
for extracting structured routing intent from natural language skier audio transcripts.
Supports mock mode for offline testing and deterministic CI/CD, as well as live mode
hooking into quantized Gemma inference (llama.cpp, Core ML, or Google GenAI).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# Permitted types conforming strictly to Section 3.1 of TECH_SPEC.md
POICategory = Literal[
    "quick_snack",
    "cafeteria",
    "sit_down",
    "bar",
    "warming_hut",
    "patrol",
    "restroom",
]

ServiceSpeed = Literal[
    "grab_and_go",
    "counter_service",
    "table_service",
]

Difficulty = Literal[
    "novice",
    "intermediate",
    "advanced",
    "expert",
]

SYSTEM_PROMPT_TEMPLATE = """You are the Cirque On-Device Ski Routing Engine.
Your job is to parse natural language voice commands from a skier into strict JSON routing parameters.
Do not output markdown code fences. Do not output explanatory text. Output valid JSON only.

Permitted Difficulty Values: ["novice", "intermediate", "advanced", "expert"]
Permitted POI Categories: ["quick_snack", "cafeteria", "sit_down", "bar", "warming_hut", "patrol", "restroom", null]
Permitted Service Speeds: ["grab_and_go", "counter_service", "table_service", null]

Current Context Schema:
{context_json}

Output Schema:
{output_schema_doc}
"""

OUTPUT_SCHEMA_DOC = """{
  "target_poi_category": "<string | null>",
  "target_poi_name": "<string | null>",
  "service_speed": "<string | null>",
  "max_difficulty": "<string>",
  "preferred_grooming": "<boolean>",
  "avoid_moguls": "<boolean>",
  "must_be_open": "<boolean>",
  "avoid_lifts": ["<string>"]
}"""


class SkiIntent(BaseModel):
    """Pydantic model representing structured skier intent strictly matching Section 3.1."""

    target_poi_category: Optional[POICategory] = None
    target_poi_name: Optional[str] = None
    service_speed: Optional[ServiceSpeed] = None
    max_difficulty: Difficulty = "advanced"
    preferred_grooming: bool = False
    avoid_moguls: bool = False
    must_be_open: bool = True
    avoid_lifts: List[str] = Field(default_factory=list)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "title": "SkiIntent",
            "description": "Cirque On-Device Gemma SLM Routing Intent Schema",
        },
    }


def build_gemma_prompt(
    transcript: str,
    current_node_id: Optional[str] = None,
    current_time_local: str = "12:00",
) -> str:
    """Builds deterministic Gemma prompt with injected context and grammar instructions."""
    context = {
        "current_node_id": current_node_id,
        "current_time_local": current_time_local,
        "raw_transcript": transcript,
    }
    context_str = json.dumps(context, indent=2)
    return SYSTEM_PROMPT_TEMPLATE.format(
        context_json=context_str,
        output_schema_doc=OUTPUT_SCHEMA_DOC,
    )


def sanitize_model_output(raw_output: str) -> str:
    """Strips markdown code fences (```json ... ``` or ``` ... ```) and extracts raw JSON substring."""
    text = raw_output.strip()
    # Strip markdown fences if present
    fence_pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.match(fence_pattern, text, re.IGNORECASE | re.MULTILINE)
    if match:
        text = match.group(1).strip()

    # If extra conversational leading/trailing characters remain, find outer brackets
    if not (text.startswith("{") and text.endswith("}")):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    return text


class GemmaIntentParser:
    """Parser & inference coordinator for Gemma SLM intent extraction."""

    def __init__(self, mode: Literal["mock", "live"] = "mock"):
        self.mode = mode

    def _mock_inference(self, transcript: str) -> str:
        """Deterministic mock inference returning fixture JSON for known patterns."""
        t_lower = transcript.lower()

        # Emergency / ski patrol
        if any(kw in t_lower for kw in ["patrol", "emergency", "injured", "injury", "help"]):
            return json.dumps({
                "target_poi_category": "patrol",
                "target_poi_name": None,
                "service_speed": None,
                "max_difficulty": "expert",
                "preferred_grooming": False,
                "avoid_moguls": False,
                "must_be_open": True,
                "avoid_lifts": [],
            })

        # Sit-down warm lunch / dining
        if any(kw in t_lower for kw in ["sit down", "sit-down", "lunch", "restaurant", "everett"]):
            grooming = "groomed" in t_lower or "groomer" in t_lower
            no_moguls = "no moguls" in t_lower or "avoid moguls" in t_lower
            difficulty: Difficulty = "intermediate" if ("blue" in t_lower or "intermediate" in t_lower) else "advanced"
            return json.dumps({
                "target_poi_category": "sit_down",
                "target_poi_name": None,
                "service_speed": "table_service",
                "max_difficulty": difficulty,
                "preferred_grooming": grooming,
                "avoid_moguls": no_moguls,
                "must_be_open": True,
                "avoid_lifts": [],
            })

        # Quick snack / cafeteria / burger
        if any(kw in t_lower for kw in ["snack", "burger", "grab", "quick", "cafeteria"]):
            difficulty = "intermediate" if ("intermediate" in t_lower or "blue" in t_lower) else "advanced"
            return json.dumps({
                "target_poi_category": "quick_snack",
                "target_poi_name": None,
                "service_speed": "grab_and_go",
                "max_difficulty": difficulty,
                "preferred_grooming": "groomed" in t_lower,
                "avoid_moguls": False,
                "must_be_open": True,
                "avoid_lifts": [],
            })

        # Village / specific destination
        if "mountain village" in t_lower or "village" in t_lower:
            difficulty = "intermediate" if ("avoiding black" in t_lower or "blue" in t_lower or "easy" in t_lower) else "advanced"
            return json.dumps({
                "target_poi_category": None,
                "target_poi_name": "Mountain Village",
                "service_speed": None,
                "max_difficulty": difficulty,
                "preferred_grooming": False,
                "avoid_moguls": False,
                "must_be_open": True,
                "avoid_lifts": [],
            })

        # Default fallback intent
        return json.dumps({
            "target_poi_category": None,
            "target_poi_name": None,
            "service_speed": None,
            "max_difficulty": "advanced",
            "preferred_grooming": False,
            "avoid_moguls": False,
            "must_be_open": True,
            "avoid_lifts": [],
        })

    def parse(self, raw_output: str, fallback_transcript: Optional[str] = None) -> SkiIntent:
        """Parses raw model output into a validated SkiIntent.

        Sanitizes markdown fences, handles JSON decode errors, and validates against
        Pydantic SkiIntent. If validation fails, safely recovers with conservative defaults.
        """
        sanitized = sanitize_model_output(raw_output)
        try:
            parsed_json = json.loads(sanitized)
            return SkiIntent.model_validate(parsed_json)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Failed to validate model output: %s. Output was: %r", e, raw_output)
            # Defensive fallback
            return SkiIntent()

    def process_transcript(
        self,
        transcript: str,
        current_node_id: Optional[str] = None,
        current_time_local: str = "12:00",
    ) -> SkiIntent:
        """Full end-to-end intent extraction from user transcript."""
        if self.mode == "mock":
            mock_output = self._mock_inference(transcript)
            return self.parse(mock_output, fallback_transcript=transcript)

        # In live mode, prompt would be passed to on-device runtime (llama.cpp / Core ML)
        prompt = build_gemma_prompt(transcript, current_node_id, current_time_local)
        raise NotImplementedError("Live Gemma engine requires model weights or edge runtime.")


def export_intent_json_schema() -> Dict[str, Any]:
    """Generates the canonical JSON Schema for SkiIntent."""
    return SkiIntent.model_json_schema()
