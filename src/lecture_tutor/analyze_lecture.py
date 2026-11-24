"""Build a topic-scoped lecture profile from a transcript and board frames."""
import argparse
import json
from pathlib import Path

from ..common.llm import generate_json, image_part
from ..lecture_profile.schemas import LECTURE_PROFILE_SCHEMA


ROOT = Path(__file__).resolve().parents[2]
PROMPT = """너는 고등학교 수학 강의 자료를 분석해 해당 강의에 한정된 지식 프로필을 만드는 분석자다.
전사문과 판서 프레임에서 강사가 실제로 설명한 개념, 관계, 적용 조건, 풀이 순서를 추출한다.

규칙:
- 제공된 전사와 프레임에 근거해 작성하고, 불명확한 내용은 uncertainties에 남긴다.
- 전사문에 없는 설명을 강사가 한 것처럼 쓰지 않는다. 수학적 오류가 의심되면 조용히 고치지 말고 불확실성에 표시한다.
- 판서만으로 강사의 말이나 의도를 추정하지 않는다. 전사와 판서가 서로 보완하는 경우에만 함께 해석한다.
- 일반적인 3차함수 지식을 강의에서 다룬 내용인 것처럼 추가하지 않는다.
- 적용 조건, 사용할 때의 순서, 성립하지 않는 경우나 주의점을 구분한다.
- evidence에는 확인 가능한 전사 구절 또는 프레임 파일명을 적는다.
- 출력은 제공된 JSON schema를 따르고, 모든 문자열은 한국어로 작성한다.
"""


def analyze_lecture(transcript_path, frames_dir, lecture_id, output_path):
    transcript_path = Path(transcript_path)
    frames_dir = Path(frames_dir)
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(f"출력 파일이 이미 있습니다: {output_path}")
    if not transcript_path.is_file():
        raise FileNotFoundError(f"전사 파일을 찾을 수 없습니다: {transcript_path}")
    frames = sorted(
        path for path in frames_dir.iterdir()
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ) if frames_dir.is_dir() else []
    if not frames:
        raise FileNotFoundError(f"판서 프레임 이미지가 없습니다: {frames_dir}")

    transcript = transcript_path.read_text(encoding="utf-8")
    contents = [
        PROMPT,
        f"강의 ID: {lecture_id}\n\n[강의 전사]\n{transcript}",
        "[시간순 판서 프레임]",
    ]
    for frame in frames:
        contents.extend([f"프레임 파일: {frame.name}", image_part(frame)])

    profile = json.loads(generate_json(contents, LECTURE_PROFILE_SCHEMA))
    profile["lecture_id"] = lecture_id
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return profile


def main():
    parser = argparse.ArgumentParser(description="전사와 판서 프레임에서 강의 프로필을 만듭니다.")
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--lecture-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    analyze_lecture(args.transcript, args.frames_dir, args.lecture_id, args.output)
    print(f"강의 프로필 저장 완료: {args.output}")


if __name__ == "__main__":
    main()
