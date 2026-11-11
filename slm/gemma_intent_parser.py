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
from typing import Any, Callable, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

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
    """Structured skier routing intent conforming to Section 3.1 of TECH_SPEC.md."""

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
    """Builds a deterministic Gemma prompt with injected location/time context and schema."""
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
    """Extracts a raw JSON object string from fenced or conversational LLM output."""
    text = raw_output.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    if not (text.startswith("{") and text.endswith("}")):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    return text


class GemmaIntentParser:
    """Deterministic mock and custom-callback coordinator for Gemma SLM intent parsing."""

    def __init__(
        self,
        mode: Literal["mock", "live"] = "mock",
        inference_fn: Optional[Callable[[str], str]] = None,
    ):
        if mode == "live" and inference_fn is None:
            raise ValueError("GemmaIntentParser(mode='live') requires an inference_fn(prompt) -> str callback.")
        self.mode = mode
        self.inference_fn = inference_fn

    def _mock_inference(self, transcript: str) -> str:
        """Deterministic rule-based fixture inference for offline CI/CD evaluation."""
        t_lower = transcript.lower()

        if any(kw in t_lower for kw in ["patrol", "emergency", "injured", "injury", "crashed"]):
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

        if any(kw in t_lower for kw in ["warming hut", "warming_hut", "freezing"]):
            return json.dumps({
                "target_poi_category": "warming_hut",
                "target_poi_name": None,
                "service_speed": None,
                "max_difficulty": "advanced",
                "preferred_grooming": False,
                "avoid_moguls": False,
                "must_be_open": True,
                "avoid_lifts": [],
            })

        if any(kw in t_lower for kw in ["restroom", "bathroom"]):
            return json.dumps({
                "target_poi_category": "restroom",
                "target_poi_name": None,
                "service_speed": None,
                "max_difficulty": "advanced",
                "preferred_grooming": False,
                "avoid_moguls": False,
                "must_be_open": True,
                "avoid_lifts": [],
            })

        if any(kw in t_lower for kw in ["bar", "beer", "après", "apres", "drink"]):
            return json.dumps({
                "target_poi_category": "bar",
                "target_poi_name": None,
                "service_speed": None,
                "max_difficulty": "advanced",
                "preferred_grooming": False,
                "avoid_moguls": False,
                "must_be_open": True,
                "avoid_lifts": [],
            })

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

        if "cafeteria" in t_lower and not any(kw in t_lower for kw in ["snack", "quick", "grab"]):
            difficulty = "intermediate" if ("intermediate" in t_lower or "blue" in t_lower) else "advanced"
            return json.dumps({
                "target_poi_category": "cafeteria",
                "target_poi_name": None,
                "service_speed": "counter_service",
                "max_difficulty": difficulty,
                "preferred_grooming": "groomed" in t_lower,
                "avoid_moguls": False,
                "must_be_open": True,
                "avoid_lifts": [],
            })

        if any(kw in t_lower for kw in ["snack", "burger", "grab", "quick"]):
            difficulty = "intermediate" if ("intermediate" in t_lower or "blue" in t_lower) else "advanced"
            return json.dumps({
                "target_poi_category": "quick_snack",
                "target_poi_name": None,
                "service_speed": "grab_and_go",
                "max_difficulty": difficulty,
                "preferred_grooming": "groomed" in t_lower or "appropriate for intermediate" in t_lower,
                "avoid_moguls": False,
                "must_be_open": True,
                "avoid_lifts": [],
            })

        if any(kw in t_lower for kw in ["steepest", "chute", "chutes", "double black", "lone peak"]):
            dest = "Lone Peak" if "lone peak" in t_lower else None
            return json.dumps({
                "target_poi_category": None,
                "target_poi_name": dest,
                "service_speed": None,
                "max_difficulty": "expert",
                "preferred_grooming": False,
                "avoid_moguls": False,
                "must_be_open": True,
                "avoid_lifts": [],
            })

        if "avoid" in t_lower and ("chair" in t_lower or "lift" in t_lower):
            avoid_lifts: List[str] = []
            if "ramcharger" in t_lower:
                avoid_lifts.append("Ramcharger 8")
            if "six shooter" in t_lower:
                avoid_lifts.append("Six Shooter")
            if "swift current" in t_lower:
                avoid_lifts.append("Swift Current 6")
            dest = "Madison Base" if "madison base" in t_lower else ("Mountain Village" if "mountain village" in t_lower else None)
            return json.dumps({
                "target_poi_category": None,
                "target_poi_name": dest,
                "service_speed": None,
                "max_difficulty": "advanced",
                "preferred_grooming": False,
                "avoid_moguls": False,
                "must_be_open": True,
                "avoid_lifts": avoid_lifts,
            })

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

    def parse(self, raw_output: str) -> SkiIntent:
        """Sanitizes and validates raw model output against SkiIntent, falling back to safe defaults on malformed JSON."""
        sanitized = sanitize_model_output(raw_output)
        try:
            parsed_json = json.loads(sanitized)
            return SkiIntent.model_validate(parsed_json)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Failed to validate model output (%s); falling back to safe defaults: %r", exc, raw_output)
            return SkiIntent()

    def process_transcript(
        self,
        transcript: str,
        current_node_id: Optional[str] = None,
        current_time_local: str = "12:00",
    ) -> SkiIntent:
        """Executes end-to-end intent extraction from a skier audio transcript."""
        if self.mode == "mock":
            return self.parse(self._mock_inference(transcript))

        prompt = build_gemma_prompt(transcript, current_node_id, current_time_local)
        assert self.inference_fn is not None
        return self.parse(self.inference_fn(prompt))


def export_intent_json_schema() -> Dict[str, Any]:
    """Generates the canonical JSON Schema for SkiIntent."""
    return SkiIntent.model_json_schema()
