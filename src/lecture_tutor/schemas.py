"""Structured output schema for mapping a problem to lecture concepts."""

from ..lecture_profile.schemas import LECTURE_PROFILE_SCHEMA


def _object(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
    }


def _array(items):
    return {"type": "array", "items": items}


def _string():
    return {"type": "string"}


DISCOVERY_SCHEMA = _object({
    "connection_level": {
        "type": "string",
        "enum": ["clear", "possible", "unclear"],
    },
    "matched_concepts": _array(_string()),
    "related_relations": _array(_string()),
    "problem_conditions": _array(_string()),
    "connection_explanation": _string(),
    "uncertainties": _array(_string()),
})


PROFILE_VALIDATION_SCHEMA = _object({
    "corrected_profile": LECTURE_PROFILE_SCHEMA,
    "relation_reviews": _array(_object({
        "relation_name": _string(),
        "status": {
            "type": "string",
            "enum": ["confirmed", "repaired", "uncertain"],
        },
        "source_support": {
            "type": "string",
            "enum": ["supported", "partially_supported", "unclear"],
        },
        "changes": _array(_string()),
        "mathematical_check": _string(),
        "remaining_uncertainties": _array(_string()),
    })),
    "global_notes": _array(_string()),
})
