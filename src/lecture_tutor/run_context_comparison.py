"""Generate no-context and raw-lecture-context answers for the current homework set."""
from pathlib import Path

from ..common.llm import generate_text, get_model_name, image_part


ROOT = Path(__file__).resolve().parents[2]
HOMEWORK_DIR = ROOT / "data/lecture_tutor/homework"
TRANSCRIPT_PATH = ROOT / "data/lecture_tutor/transcripts/cubic_ratio.txt"
FRAMES_DIR = ROOT / "data/lecture_tutor/frames/cubic_ratio"
OUTPUT_DIR = ROOT / "data/lecture_tutor/evaluation"

ANSWER_PROMPT = """너는 고등학교 수학 문제를 정확히 풀고 설명하는 튜터다.
첨부된 문제 이미지의 조건과 물음을 먼저 정확히 읽고, 논리와 계산을 확인하면서 풀이하라.
강의 자료가 제공된 경우 문제 풀이에 실제로 적용되는 내용만 사용하고, 연결이 약하면 억지로 적용하지 않는다.
필요한 풀이를 한국어로 제시하고 마지막에 최종 답을 명확히 표시한다.
"""


def generate_for_problem(problem_path: Path, with_lecture: bool) -> str:
    contents = [ANSWER_PROMPT]
    if with_lecture:
        transcript = TRANSCRIPT_PATH.read_text(encoding="utf-8")
        contents.extend(["[강의 원자료: STT 전사]", transcript,
                         "[시간순 판서 프레임]"])
        frames = sorted(
            path for path in FRAMES_DIR.iterdir()
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        )
        for frame in frames:
            contents.extend([f"판서 프레임 {frame.name}", image_part(frame)])
    contents.extend(["[풀이할 숙제 문제]", image_part(problem_path)])
    return generate_text(contents)


def main():
    if not TRANSCRIPT_PATH.is_file() or not FRAMES_DIR.is_dir():
        raise FileNotFoundError("강의 전사 또는 판서 프레임을 찾을 수 없습니다.")
    problems = sorted(
        path for path in HOMEWORK_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )
    for condition in ("no_lecture", "raw_lecture"):
        (OUTPUT_DIR / condition).mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "conditions.txt").write_text(
        f"model={get_model_name()}\n"
        "no_lecture: problem image + shared answer prompt\n"
        "raw_lecture: STT transcript + all sampled board frames + problem image + shared answer prompt\n"
        "profile_route: pre-existing discoveries/ and solutions/ outputs\n",
        encoding="utf-8",
    )

    for problem in problems:
        for condition, with_lecture in (("no_lecture", False), ("raw_lecture", True)):
            output_path = OUTPUT_DIR / condition / f"{problem.stem}.md"
            if output_path.exists():
                print(f"이미 있음, 건너뜀: {output_path.relative_to(ROOT)}")
                continue
            print(f"생성 중: {condition}/{problem.stem}", flush=True)
            answer = generate_for_problem(problem, with_lecture)
            output_path.write_text(answer + "\n", encoding="utf-8")
            print(f"저장: {output_path.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
