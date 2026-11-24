"""Structured observations and deterministic, per-Step teaching counts."""
import json

IDS = [f"T{i:02d}" for i in range(1, 13)] + ["OTHER"]
STATES = ["관찰됨", "해당 장면에서 관찰되지 않음", "판단 불가", "해당 없음"]
TIMINGS = ["관련 행동 전", "실행 중", "실행 후", "풀이 종료 후", "판단 불가"]
EXTENTS = ["짧은 언급", "연결 설명", "상세 전개", "판단 불가"]

def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties)}

def arr(items):
    return {"type": "array", "items": items}

def string(values=None):
    result = {"type": "string"}
    if values:
        result["enum"] = values
    return result

LINES = arr({"type": "integer"})
OBSERVATION = obj({
    "id": string(IDS), "status": string(STATES), "lines": LINES,
    "situation": string(), "description": string(),
    "timing": string(TIMINGS), "extent": string(EXTENTS),
    "extent_basis": string(), "subtype": string(),
    "action_target": string(), "reason": string(), "uncertainty": string(),
})
SCHEMA = obj({
    "problem_observations": arr(obj({"text": string(), "lines": LINES})),
    "steps": arr(obj({
        "trigger": string(), "trigger_lines": LINES,
        "action": string(), "lines": LINES,
        "teaching_action": string(), "observations": arr(OBSERVATION),
    })),
    "unobserved_checks": arr(obj({
        "id": string(IDS), "status": string(STATES[1:]),
        "lines": LINES, "reason": string(),
    })),
    "notes": arr(obj({"text": string(), "lines": LINES})),
})

def validate(data, transcript):
    """Validate shape and references, not the correctness of pedagogical judgments."""
    def walk(value, schema, path):
        kind = schema["type"]
        if kind == "object":
            if not isinstance(value, dict) or set(value) != set(schema["properties"]):
                raise ValueError(f"{path}: fields do not match schema")
            for key, child in schema["properties"].items():
                walk(value[key], child, f"{path}.{key}")
        elif kind == "array":
            if not isinstance(value, list):
                raise ValueError(f"{path}: expected list")
            for index, item in enumerate(value):
                walk(item, schema["items"], f"{path}[{index}]")
        elif kind == "integer":
            if type(value) is not int:
                raise ValueError(f"{path}: expected integer")
        elif not isinstance(value, str):
            raise ValueError(f"{path}: expected string")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{path}: invalid category")

    walk(data, SCHEMA, "analysis")
    size = len(transcript.splitlines())

    def references(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ("lines", "trigger_lines"):
                    if len(child) != len(set(child)) or any(n < 1 or n > size for n in child):
                        raise ValueError(f"Invalid transcript references: {child}")
                else:
                    references(child)
        elif isinstance(value, list):
            for child in value:
                references(child)
    references(data)
    if not data["steps"]:
        raise ValueError("No Policy Trace steps")
    for step in data["steps"]:
        if not step["lines"] or not step["action"].strip() or not step["trigger"].strip():
            raise ValueError("Each Step needs action, trigger and evidence")
        for observation in step["observations"]:
            if observation["status"] == "관찰됨":
                if not observation["lines"] or not observation["description"].strip():
                    raise ValueError("Observed behavior needs evidence and description")
                if observation["id"] == "T02" and not all(
                    observation[k].strip() for k in ("action_target", "reason")
                ):
                    raise ValueError("T02 needs action_target and reason")
                if observation["id"] == "OTHER" and not observation["subtype"].strip():
                    raise ValueError("OTHER needs subtype")
    checks = [item["id"] for item in data["unobserved_checks"]]
    if len(checks) != len(set(checks)):
        raise ValueError("Duplicate unobserved check")
    present = {o["id"] for s in data["steps"] for o in s["observations"] if o["status"] == "관찰됨"}
    if present.intersection(checks):
        raise ValueError("Observed category also declared globally unobserved")
    if not set(IDS[:-1]).issubset(present | set(checks)):
        raise ValueError("Missing category assessment")
    return data

def aggregate(data):
    rows = []
    for category in IDS:
        observed = []
        local = []
        for index, step in enumerate(data["steps"], 1):
            for item in step["observations"]:
                if item["id"] == category:
                    (observed if item["status"] == "관찰됨" else local).append((f"S{index:02d}", item))
        checks = [x for x in data["unobserved_checks"] if x["id"] == category]
        step_ids = list(dict.fromkeys(s for s, _ in observed))
        if category == "OTHER" and not observed and not local and not checks:
            continue
        status = "관찰됨" if observed else (checks[0]["status"] if checks else "미평가")
        rows.append({
            "id": category, "status": status, "count": len(step_ids), "step_ids": step_ids,
            "situations": list(dict.fromkeys(o["situation"] for _, o in observed)),
            "timing_extent": list(dict.fromkeys(f'{s}: {o["timing"]} / {o["extent"]}' for s, o in observed)),
            "limitations": [f'{s}: {o["status"]} — {o["description"]}' for s, o in local]
                + [f'{s}: {o["uncertainty"]}' for s, o in observed if o["uncertainty"].strip() not in ("", "없음")]
                + [x["reason"] for x in checks],
        })
    return rows

def render(data, transcript):
    lines = transcript.splitlines()
    def evidence(numbers):
        return "\n".join(f'> [L{n:04d}] {lines[n-1]}' for n in sorted(numbers))
    def cell(value):
        return str(value).replace("|", "&#124;").replace("\n", "<br>")
    out = ["### [문제풀이 관찰]", ""]
    for item in data["problem_observations"]:
        out += [item["text"], evidence(item["lines"]), ""]
    out += ["### [Policy Trace]", ""]
    for index, step in enumerate(data["steps"], 1):
        out += [f"**Step S{index:02d}**", "",
                f'- **Trigger**: {step["trigger"]}', evidence(step["trigger_lines"]),
                f'- **Action**: {step["action"]}',
                f'- **Teaching Action**: {step["teaching_action"]}',
                "**Evidence**", evidence(step["lines"]), ""]
        for item in step["observations"]:
            out += [f'- **{item["id"]} / {item["status"]}**: {item["description"]}',
                    f'  - 상황: {item["situation"]}',
                    f'  - 시점·분량: {item["timing"]} / {item["extent"]}',
                    f'  - 분량 근거: {item["extent_basis"]}']
            if item["subtype"]:
                out += [f'  - 하위 유형: {item["subtype"]}']
            if item["id"] == "T02":
                out += [f'  - 선택 행동 / 이유: {item["action_target"]} / {item["reason"]}']
            if item["uncertainty"]:
                out += [f'  - 불확실성: {item["uncertainty"]}']
            out += [evidence(item["lines"]), ""]
    out += ["### [교수 행동 점검표 — 코드 집계]", "",
            "관찰 장면 수는 해당 행동이 관찰된 고유 Step 수다. 같은 Step의 동일 ID는 한 번만 센다.",
            "Step 분할에 의존하며, 적용률이나 정밀한 발화 빈도가 아니다. 0회는 사용하지 않는 성향을 뜻하지 않는다.", "",
            "| ID | 관찰 상태 | 관찰 장면 수 | Step IDs | 적용 상황 | 시점·분량 | 비관찰·불확실성 |",
            "|---|---|---|---|---|---|---|"]
    for row in aggregate(data):
        values = [row["id"], row["status"], row["count"], ", ".join(row["step_ids"]) or "-",
                  "; ".join(row["situations"]) or "-", "; ".join(row["timing_extent"]) or "-",
                  "; ".join(row["limitations"]) or "-"]
        out.append("| " + " | ".join(cell(x) for x in values) + " |")
    out += ["", "### [추가 관찰 및 통합 시 주의점]", ""]
    for note in data["notes"]:
        out += [note["text"], evidence(note["lines"]), ""]
    return "\n".join(out)

