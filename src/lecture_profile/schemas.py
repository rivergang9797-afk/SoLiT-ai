"""Structured output contracts for lecture-specific knowledge."""


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


LECTURE_PROFILE_SCHEMA = _object({
    "lecture_id": _string(),
    "topic": _string(),
    "scope": _string(),
    "core_concepts": _array(_string()),
    "relations": _array(_object({
        "name": _string(),
        "statement": _string(),
        "applicability_conditions": _array(_string()),
        "use_steps": _array(_string()),
        "cautions": _array(_string()),
        "evidence": _array(_string()),
    })),
    "lecture_examples": _array(_string()),
    "notation_and_graph_conventions": _array(_string()),
    "uncertainties": _array(_string()),
})
