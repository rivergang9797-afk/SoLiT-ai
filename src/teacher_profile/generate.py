import os
import argparse
import tempfile
import shutil
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


# =========================================================
# Environment
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY를 찾을 수 없습니다.")

client = genai.Client(api_key=api_key)

MODEL_NAME = "gemini-3.6-flash"


# =========================================================
# File utilities
# =========================================================

def get_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()

    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }

    if suffix not in mime_map:
        raise ValueError(
            f"지원하지 않는 이미지 형식입니다: {suffix}"
        )

    return mime_map[suffix]


def load_image_part(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"문제 이미지가 없습니다: {path}")

    return types.Part.from_bytes(
        data=path.read_bytes(),
        mime_type=get_mime_type(path)
    )


def load_teacher_policy(
    policy_path: str = "data/teacher_profile/profiles/teacher_policy_v4.md"
) -> str:

    path = ROOT / policy_path

    if not path.exists():
        raise FileNotFoundError(
            f"Teacher Policy 파일이 없습니다: {path}"
        )

    return path.read_text(encoding="utf-8")


# =========================================================
# Few-shot examples
# =========================================================

FEWSHOT_IDS = [
    "001",
    "004",
    "013",
]


def load_fewshot_examples():
    example_dir = ROOT / "data" / "teacher_profile" / "fewshot_examples"

    contents = []

    for example_id in FEWSHOT_IDS:

        transcript_path = example_dir / f"{example_id}.txt"

        image_path = None

        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            candidate = example_dir / f"{example_id}{ext}"

            if candidate.exists():
                image_path = candidate
                break

        if image_path is None:
            raise FileNotFoundError(
                f"Few-shot 문제 이미지를 찾을 수 없습니다: {example_id}"
            )

        if not transcript_path.exists():
            raise FileNotFoundError(
                f"Few-shot 해설 transcript를 찾을 수 없습니다: {transcript_path}"
            )

        teacher_solution = transcript_path.read_text(
            encoding="utf-8"
        )

        contents.append(
            f"""
==============================
FEW-SHOT EXAMPLE {example_id}
==============================

아래 이미지는 실제 강사가 풀이한 문제이다.
"""
        )

        contents.append(
            load_image_part(image_path)
        )

        contents.append(
            f"""
[실제 강사 풀이]

{teacher_solution}
"""
        )

    return contents


# =========================================================
# Prompts
# =========================================================

BASELINE_PROMPT = """
너는 수학 문제를 풀이하고 학생에게 설명하는 수학 강사다.

첨부된 문제를 정확하게 해결하라.

문제를 해결하는 데 적절한 풀이 전략을 스스로 선택하고,
학생이 이해할 수 있도록 자연스럽게 설명하라.

정답뿐 아니라 풀이 과정을 충분히 제시하라.

특정 강사의 스타일을 의도적으로 모방하지 마라.
"""


FEWSHOT_PROMPT = """
너는 수학 문제를 풀이하고 학생에게 설명하는 AI Tutor다.

아래에는 동일한 한 명의 수학 강사가
실제로 여러 수학 문제를 풀이한 예시가 주어진다.

각 예시는

문제 이미지
+
실제 강사의 해설

로 구성되어 있다.

너의 목표는 이 예시들을 단순히 복사하는 것이 아니다.

예시들을 관찰하여 이 강사가

- 문제를 처음 보고 어떤 전략을 선택하는지
- 어떤 조건에서 풀이 방향을 바꾸는지
- 어떤 표현으로 문제를 재구성하는지
- 어떤 부분을 학생에게 강조하는지
- 어떤 말투와 표현을 반복적으로 사용하는지

를 파악하고,

마지막에 제시되는 새로운 문제도
같은 강사가 실제로 풀이하는 것처럼 해결하고 설명하라.

중요:

1. 예시의 문제와 새 문제는 서로 다른 문제다.
   숫자나 식을 그대로 복사하지 마라.

2. 예시에서 관찰되는 행동 패턴만 일반화하라.

3. 새로운 문제에서는 문제에 맞는 정확한 수학적 풀이를 우선한다.

4. 실제 강사의 풀이 전략과 설명 방식을 최대한 재현하되,
   존재하지 않는 행동을 임의로 만들어내지 마라.

5. 최종 출력에서는
   "예시를 참고했다",
   "few-shot",
   "강사 스타일"

   같은 메타적인 표현을 하지 마라.

실제 수학 강의처럼 자연스럽게 하나의 완성된 풀이를 작성하라.
"""


def build_policy_prompt(teacher_policy: str) -> str:

    return f"""
너는 수학 문제를 풀이하고 학생에게 설명하는 AI Tutor다.

아래에는 실제 한 수학 강사의 여러 문제 풀이에서 추출된
Teacher Policy Representation이 주어진다.

너의 목표는 단순히 정답을 구하는 것이 아니다.

새로운 문제를 해결하면서 Teacher Policy Representation에 기록된
강사의 Problem-solving Policy와 Teaching Policy를 적용하여,

"이 강사가 실제로 이 문제를 처음 보고 풀었다면
어떤 풀이 행동을 선택하고 어떻게 설명했을지"

를 최대한 재현하라.


==================================================
중요 원칙
==================================================

1. 문제를 먼저 직접 분석한다.

Teacher Policy를 억지로 적용해서는 안 된다.
현재 문제 상황과 Policy의 Trigger가 실제로 일치할 때만
해당 Policy를 실행한다.


2. 문제 전체를 하나의 유형으로만 분류하지 않는다.

풀이가 진행되면서 새로운 수학적 조건이나 구조가 등장하면
새로운 Trigger가 발생할 수 있다.

따라서 하나의 문제에서 여러 Policy가
순차적으로 실행될 수 있다.


3. Problem-solving Policy는 실제 풀이 선택에 반영한다.

단순히 Policy를 설명하는 것이 아니라,

어떤 식을 먼저 만들지,
어떤 조건을 먼저 볼지,
그래프를 그릴지,
케이스를 나눌지,
어떤 표현으로 문제를 재구성할지

등 실제 문제 해결 행동에 적용한다.


4. Teaching Policy는 설명 행동에 적용한다.

강사가

- 어떤 부분을 먼저 강조하는지
- 어떤 행동을 습관으로 만들도록 말하는지
- 어떤 실수를 미리 지적하는지
- 어떤 그래프 언어를 사용하는지
- 어떤 계산의 정당성을 설명하는지

를 반영한다.


5. Policy에 존재하지 않는 상황에서는
일반적인 수학적 추론을 사용하여 문제를 정확하게 해결한다.

Teacher Policy에 없는 행동을
강사의 특징인 것처럼 임의로 만들어내지 않는다.


6. Representative Quote를 무조건 복사하지 않는다.

문맥에 자연스럽게 맞는 경우에만
강사의 표현 습관을 활용한다.

표면적인 말투 복사보다
풀이 선택과 설명 행동의 재현을 우선한다.


7. 내부적으로 어떤 Policy를 사용했는지 판단하되,
학생에게 보여주는 최종 답변에서는

"G-P1을 적용하겠습니다"
"L-P1을 사용합니다"

같은 Policy ID나 시스템 정보를 언급하지 않는다.

실제 수학 강의처럼 자연스럽게 설명한다.


8. 최종 출력은 학생에게 실제로 문제를 해설하는
하나의 완성된 강의 형태로 작성한다.


9. 회고는 선택적으로 한다.

아래 회고 지침은 강사가 직접 지정한 운영 지침이며,
영상에서 추출된 강사의 습관으로 해석하지 않는다.
Teacher Policy가 회고를 일률적으로 요구하더라도 이 지침을 우선한다.

풀이 전체를 다시 요약하지 말고, 학생이 다른 문제에 활용할
핵심 판단이나 적용 조건을 되짚을 필요가 있을 때만 덧붙인다.
풀이가 짧아 복기할 필요가 없거나, 풀이 중 이미 충분히 강조했다면 생략한다.


10. 해설 분량은 강사의 설명 성향과 현재 문제의 난이도를 함께 고려하여 결정한다.

이 역시 강사가 직접 지정한 운영 지침이다.
Teacher Policy에서 근거가 확인된 설명 성향을 기준으로 삼되,
현재 문제의 난이도와 각 추론의 어려움에 맞추어 설명의 상세도를 조절한다.
관찰 자료에 없는 강사의 성향을 임의로 추정하지 않는다.
문제의 길이나 계산 단계 수만으로 난이도를 판단하지 않는다.
풀이 방법을 선택하거나 바꾸는 지점, 조건에서 바로 드러나지 않는 결론을
도출하는 지점에서는 왜 그렇게 하는지 설명한다.
이미 설명한 방법의 반복 적용이나 단순 계산은 짧게 진행한다.


==================================================
Teacher Policy Representation
==================================================

{teacher_policy}


==================================================
새로운 문제
==================================================

첨부된 문제를 위 Teacher Policy에 따라 풀고 설명하라.
"""


# =========================================================
# Generation
# =========================================================

def generate_answer(
    problem_path: Path,
    prompt: str
) -> str:

    image_part = load_image_part(problem_path)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            prompt,
            image_part
        ],
        config=types.GenerateContentConfig(
            temperature=0.2,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
    )

    if not response.text:
        raise RuntimeError(
            "Gemini 응답에서 텍스트를 얻지 못했습니다."
        )

    return response.text


def generate_fewshot_answer(
    problem_path: Path
) -> str:

    contents = [
        FEWSHOT_PROMPT
    ]

    contents.extend(
        load_fewshot_examples()
    )

    contents.append(
        """
==============================
NEW PROBLEM
==============================

이제 아래 새로운 문제를
앞선 실제 강사 예시에서 관찰한 풀이 및 설명 방식을 바탕으로
해결하고 설명하라.
"""
    )

    contents.append(
        load_image_part(problem_path)
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.2,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
    )

    if not response.text:
        raise RuntimeError(
            "Gemini Few-shot 응답에서 텍스트를 얻지 못했습니다."
        )

    return response.text


# =========================================================
# Experiment
# =========================================================

def get_policy_version(policy_path: str, version: str | None = None) -> str:
    if version is None:
        stem = Path(policy_path).stem
        match = re.search(r"_v(\d+)$", stem, re.IGNORECASE)
        if match:
            version = "V" + match.group(1)
        elif stem == "teacher_policy":
            version = "V1"
        else:
            raise ValueError("정책 파일명에서 버전을 확인할 수 없습니다. --policy-version V4처럼 지정해 주세요.")
    if not re.fullmatch(r"[vV]\d+", version):
        raise ValueError("정책 버전은 V1, V4 같은 형식이어야 합니다.")
    return "V" + version[1:]


def save_result(path: Path, content: str):
    """Save complete output and preserve any previous version before replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".generation-", delete=False) as temporary:
        temporary_path = Path(temporary.name)
        temporary.write(content)
    try:
        if path.exists():
            history = path.parent / ".history"
            history.mkdir(exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=history, prefix=f"{path.stem}_{datetime.now():%Y%m%d_%H%M%S_%f}_",
                suffix=path.suffix, delete=False,
            ) as backup:
                backup_path = Path(backup.name)
            shutil.copyfile(path, backup_path)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def run_experiment(
    problem_path: Path, policy_only: bool = False,
    output_root: Path | None = None,
    policy_path: str = "data/teacher_profile/profiles/teacher_policy_v4.md",
    policy_version: str | None = None,
):

    problem_id = problem_path.stem

    policy_version = get_policy_version(policy_path, policy_version)
    if output_root is None:
        output_root = ROOT / "data" / "teacher_profile" / "generations"
    output_dir = output_root / problem_id

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    teacher_policy = load_teacher_policy(policy_path)

    print("=" * 60)
    print(f"Problem: {problem_id}")
    print("=" * 60)


    # -----------------------------------------------------
    # 1. Baseline
    # -----------------------------------------------------

    if not policy_only:
        print("\n[1/3] Generating baseline...")

        baseline = generate_answer(
            problem_path,
            BASELINE_PROMPT
        )

        baseline_path = output_dir / "baseline.txt"

        save_result(baseline_path, baseline)

        print(f"[DONE] {baseline_path}")


        # -----------------------------------------------------
        # 2. Few-shot
        # -----------------------------------------------------

        print("\n[2/3] Generating few-shot answer...")

        fewshot = generate_fewshot_answer(
            problem_path
        )

        fewshot_path = output_dir / "fewshot.txt"

        save_result(fewshot_path, fewshot)

        print(f"[DONE] {fewshot_path}")


    # -----------------------------------------------------
    # 3. Teacher Policy
    # -----------------------------------------------------

    print(
        "\n[1/1] Generating policy-conditioned answer..."
        if policy_only else "\n[3/3] Generating policy-conditioned answer..."
    )

    policy_prompt = build_policy_prompt(
        teacher_policy
    )

    policy_answer = generate_answer(
        problem_path,
        policy_prompt
    )

    policy_output = output_dir / f"policy{policy_version}.txt"
    save_result(policy_output, policy_answer)

    print(f"[DONE] {policy_output}")


    print(f"Results saved to: {output_dir}")


# =========================================================
# Main
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="테스트 문제 해설 생성")
    parser.add_argument(
        "--policy-only", action="store_true",
        help="baseline과 few-shot 생성 없이 문항 폴더에 정책 버전별 해설만 저장",
    )
    parser.add_argument(
        "--policy", default="data/teacher_profile/profiles/teacher_policy_v4.md",
        help="적용할 정책 파일 (기본: data/teacher_profile/profiles/teacher_policy_v4.md)",
    )
    parser.add_argument(
        "--ids", nargs="+",
        help="생성할 문제 ID (예: test005 또는 test001 test005)",
    )
    parser.add_argument(
        "--policy-version", help="출력 정책 버전 (예: V4). 기본은 정책 파일명에서 자동 판별",
    )
    parser.add_argument(
        "--output-dir", default="data/teacher_profile/generations",
        help="결과 저장 폴더 (기본: data/teacher_profile/generations)",
    )
    args = parser.parse_args()

    test_dir = ROOT / "data" / "teacher_profile" / "test_problems"

    if not test_dir.exists():
        raise FileNotFoundError(
            f"테스트 문제 폴더가 없습니다: {test_dir}"
        )

    image_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp"
    }

    problem_paths = sorted(
        path
        for path in test_dir.iterdir()
        if path.suffix.lower() in image_extensions
    )

    if not problem_paths:
        raise ValueError(
            f"테스트 문제가 없습니다: {test_dir}"
        )

    if args.ids:
        selected_ids = set(args.ids)
        missing_ids = selected_ids - {path.stem for path in problem_paths}
        if missing_ids:
            parser.error("테스트 문제를 찾을 수 없음: " + ", ".join(sorted(missing_ids)))
        problem_paths = [path for path in problem_paths if path.stem in selected_ids]

    try:
        policy_version = get_policy_version(args.policy, args.policy_version)
        teacher_policy = load_teacher_policy(args.policy)
    except (ValueError, FileNotFoundError) as error:
        parser.error(str(error))
    output_root = ROOT / args.output_dir
    print(f"Results directory: {output_root}")
    print(f"Found {len(problem_paths)} test problems.")

    for i, problem_path in enumerate(problem_paths, start=1):

        print("\n")
        print("#" * 70)
        print(
            f"[{i}/{len(problem_paths)}] "
            f"Running {problem_path.name}"
        )
        print("#" * 70)

        try:
            run_experiment(
                problem_path, policy_only=args.policy_only,
                output_root=output_root, policy_path=args.policy,
                policy_version=policy_version,
            )

        except Exception as e:
            print(f"[ERROR] {problem_path.name}: {e}")
            continue

    print("\nAll experiments finished.")
