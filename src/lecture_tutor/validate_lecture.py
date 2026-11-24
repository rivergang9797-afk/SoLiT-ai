"""Repair ambiguous or misstated mathematics in an extracted lecture profile."""
import argparse
import json
from pathlib import Path

from ..common.llm import generate_json, image_part
from .schemas import PROFILE_VALIDATION_SCHEMA


ROOT = Path(__file__).resolve().parents[2]
PROMPT = """너는 고등학교 수학 강의에서 추출한 강의 프로필을 수학적으로 검토하고 보완한다.
입력 프로필은 강의의 핵심 내용을 대체로 담았지만, 영상 프레임 판독과 STT 오류 때문에
정의·조건·기호가 불완전하거나 표현이 부정확할 수 있다. 이런 경우 오류 문장을 즉시 삭제하지 말고,
강의 맥락과 수학적 유도를 함께 사용해 의도된 관계와 빠진 조건을 복원한다.

[검토 원칙]
- 각 relation을 독립적으로 검토한다. 결론만 맞다고 선언하지 말고, 적용 조건이 성립하는 이유를 수식이나 논리로 확인한다.
- 강의 전사·판서가 뒷받침하는 내용과 수학적으로 참인 내용을 별도로 판단한다.
- 수학적으로 참이지만 조건이 빠진 주장은 조건을 보완해 corrected_profile에 기록하고 status='repaired'로 표시한다.
- 말이 잘못 인식된 것으로 보이면 주변 전사와 프레임을 대조해 표기·용어를 복원한다.
- 강의의 의도와 수학적 조건을 합리적으로 복원할 수 있으면 보완한다. 확정할 수 없는 부분만 uncertainties에 남기고 status='uncertain'으로 표시한다.
- 원래 관계가 명백히 틀렸더라도, 인접 문맥에서 의도된 올바른 관계를 추론할 수 있으면 이를 수정하고 수정 내역을 기록한다. 임의의 새 공식을 만들어 대체하지 않는다.
- 관계를 삭제하지 않는다. 복원 불가능한 관계는 후보로 남겨 uncertainty를 표시하고, 답변 생성에서 단정적으로 사용하지 않도록 global_notes에 적는다.
- lecture_examples, core_concepts, applicability_conditions 등도 수학적으로 검토한다. 수정한 값은 changes에 구체적으로 기록한다.
- 근거가 없는 일반 수학 지식을 해당 강의에서 가르친 내용으로 추가하지 않는다.
- 출력의 corrected_profile은 입력 프로필의 구조를 유지하고 제공된 schema를 따른다. 모든 내용은 한국어로 작성한다.

[해당 프로필에 3차함수 1:√3 관계가 있을 때]
이 관계를 '변곡점을 지나는 아무 직선에서 항상 성립'한다고 무조건 확정하지 않는다.
직선을 빼서 g(x)=f(x)-L(x)로 놓고 변곡점의 x좌표를 원점으로 옮겨 유도한다.
교점의 개수와 실수 접선 조건을 확인한다. 관계가 성립하는 경우에는 원래 함수의 극값이라고
뭉뚱그리지 말고, L과 평행한 접선의 접점과 대응하는 바깥쪽 교점을 구분한다.
적용 조건과 비교하는 x좌표 거리를 정확히 적고, 불필요하게 더 넓은 조건으로 일반화하지 않는다.
"""


def validate_lecture_profile(draft_path, transcript_path, frames_dir, output_path, report_path):
    draft_path = Path(draft_path)
    transcript_path = Path(transcript_path)
    frames_dir = Path(frames_dir)
    output_path = Path(output_path)
    report_path = Path(report_path)

    if not draft_path.is_file():
        raise FileNotFoundError(f"강의 프로필 초안을 찾을 수 없습니다: {draft_path}")
    if not transcript_path.is_file():
        raise FileNotFoundError(f"전사 파일을 찾을 수 없습니다: {transcript_path}")
    if output_path.exists() or report_path.exists():
        raise FileExistsError("검증 출력 파일이 이미 있습니다. 다른 경로를 지정해 주세요.")

    frames = sorted(
        path for path in frames_dir.iterdir()
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ) if frames_dir.is_dir() else []
    if not frames:
        raise FileNotFoundError(f"판서 프레임 이미지가 없습니다: {frames_dir}")

    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    transcript = transcript_path.read_text(encoding="utf-8")
    contents = [
        PROMPT,
        "[추출된 강의 프로필 초안]\n" + json.dumps(draft, ensure_ascii=False, indent=2),
        "[강의 전사]\n" + transcript,
        "[시간순 판서 프레임]",
    ]
    for frame in frames:
        contents.extend([f"프레임 파일: {frame.name}", image_part(frame)])

    result = json.loads(generate_json(contents, PROFILE_VALIDATION_SCHEMA))
    corrected = result["corrected_profile"]
    corrected["lecture_id"] = draft.get("lecture_id", corrected.get("lecture_id", ""))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(corrected, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps({
            "lecture_id": corrected["lecture_id"],
            "relation_reviews": result["relation_reviews"],
            "global_notes": result["global_notes"],
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return corrected, result


def main():
    parser = argparse.ArgumentParser(description="추출된 강의 프로필을 수학적으로 검토·보완합니다.")
    parser.add_argument("--draft", required=True, help="analyze_lecture가 생성한 원본 프로필")
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--output", required=True, help="보완된 최종 프로필 JSON")
    parser.add_argument("--report", required=True, help="관계별 검증·수정 기록 JSON")
    args = parser.parse_args()
    _corrected, result = validate_lecture_profile(
        args.draft, args.transcript, args.frames_dir, args.output, args.report
    )
    print(f"보완 프로필 저장: {args.output}")
    print(f"검증 기록 저장: {args.report}")
    print(f"관계 검토 수: {len(result['relation_reviews'])}")


if __name__ == "__main__":
    main()
