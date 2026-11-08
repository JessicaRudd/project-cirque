"""
Project Cirque: Code Snippet from STEP_1_1
Module: pipeline/fetch_ski_data.py
Highlight: Bounding Box Envelope Verification & Difficulty Normalization
"""

from typing import Any, Dict, Optional

BIG_SKY_BBOX = {
    "south": 45.2300,
    "west": -111.4700,
    "north": 45.3200,
    "east": -111.3400,
}

DIFFICULTY_NORMALIZATION = {
    "beginner": "novice",
    "green": "novice",
    "easy": "novice",
    "intermediate": "intermediate",
    "blue": "intermediate",
    "advanced": "advanced",
    "black": "advanced",
    "expert": "expert",
    "double_black": "expert",
    "freeride": "freeride",
    "extreme": "freeride",
}


def normalize_piste_difficulty(raw_diff: Optional[str], tags: Dict[str, Any]) -> str:
    """Enforce zero empty difficulty tags by normalizing synonyms or inferring from terrain tags."""
    if raw_diff:
        cleaned = raw_diff.strip().lower().replace("-", "_").replace(" ", "_")
        if cleaned in DIFFICULTY_NORMALIZATION:
            return DIFFICULTY_NORMALIZATION[cleaned]

    name = (tags.get("name") or "").lower()
    if any(k in name for k in ["couloir", "chute", "headwall", "pinnacle", "gully"]):
        return "freeride"
    if any(k in name for k in ["bowl", "ridge", "bluff", "cirque"]):
        return "advanced"
    if any(k in name for k in ["easy", "beginner", "learning", "magic", "mr. k"]):
        return "novice"

    return "intermediate"
