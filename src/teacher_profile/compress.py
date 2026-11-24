import os
import json
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY를 찾을 수 없습니다.")

client = genai.Client(api_key=api_key)


def load_teacher_policy(
    policy_path="data/teacher_profile/profiles/teacher_policy.md"
):
    path = ROOT / policy_path

    if not path.exists():
        raise FileNotFoundError(f"파일이 없습니다: {path}")

    return path.read_text(encoding="utf-8")


def compress_policy(policy_text: str) -> str:

    prompt = """
너는 AI Tutor 및 LLM personalization 연구를 수행하는 AI 연구자다.

입력으로 한 수학 강사의 상세 Teacher Policy Representation이 주어진다.

이 문서는 여러 문제의 해설 분석을 통합하여 만들어졌으며,
Problem-solving Policy와 Teaching Policy,
Global / Topic-specific Policy,
근거 문장과 빈도 정보를 포함하고 있다.

당신의 목적은 이 정보를 버리는 단순 요약이 아니다.

향후 새로운 수학 문제를 LLM에게 제시했을 때,
이 강사와 유사한 문제 풀이 선택과 설명 방식을 재현하기 위해 사용할
"실행 가능한 Teacher Policy Representation"을 만들어야 한다.


==================================================
핵심 원칙
==================================================

1. Policy는 두 개의 독립된 축을 동시에 가진다.

scope:
- global
- local

type:
- problem_solving
- teaching

따라서 최종적으로 다음 네 그룹으로 분류한다.

- global_problem_solving
- global_teaching
- local_problem_solving
- local_teaching


2. 각 Policy의 핵심 정보는 반드시 보존한다.

각 Policy에는 다음 필드를 포함한다.

id:
Policy 고유 ID

name:
짧은 Policy 이름

scope:
global 또는 local

topic:
local인 경우 적용되는 단원/유형
global이면 null

trigger:
어떤 상황에서 Policy를 실행하는지

action:
실제로 수행해야 하는 행동

teaching_behavior:
그 행동을 학생에게 어떤 방식으로 전달하는지
Problem-solving Policy라도 관련된 설명 행동이 있으면 기록

preferred_phrases:
강사가 실제로 자주 사용하는 표현이나 표현 스타일

examples:
실제 강사 발화에서 가져온 대표 예시 1~3개

confidence:
high / medium / low


3. action은 반드시 실행 가능한 형태로 작성한다.

나쁜 예:
"그래프 중심으로 사고한다."

좋은 예:
"실근 개수 조건이 나오면 방정식을 그래프와 가로선의 교점 개수로 바꾸어 해석한다."


4. teaching_behavior는 설명 스타일을 구체적으로 기록한다.

나쁜 예:
"직관적으로 설명한다."

좋은 예:
"대수 조건을 '접한다', '뚫는다', '꺾인다'와 같은 그래프 언어로 바꾸어 설명한다."


5. preferred_phrases에는 실제 강사의 표현 습관만 넣는다.

예:
- "당연히"
- "습관적으로"
- "기본으로 해놓고"
- "~하면 되죠"
- "떠올려 줘야 됩니다"

단, 특정 한 문제에서만 우연히 사용한 표현은 제외한다.


6. examples는 실제 입력 문서의 대표 근거 문장을 사용한다.

문장을 새로 만들어내지 마라.

각 Policy당 최대 3개만 보존한다.


7. 중복 Policy는 반드시 통합한다.

예를 들어

- 정적분 정의 함수에서 대입한다
- 정적분 정의 함수에서 미분한다
- 대입과 미분을 기본 루틴으로 한다

는 하나의 Policy로 통합한다.


8. Problem-solving Policy와 Teaching Policy가 강하게 결합되어 있더라도
무리하게 하나로 합치지 마라.

대신 서로의 관련성을 related_policies 필드로 연결한다.


9. 상세 문서의 모든 내용을 보존할 필요는 없다.

다음은 제거한다.

- 긴 수학 풀이 과정
- 문제별 세부 계산
- 반복되는 설명
- 추상적 성격 평가
- 연구 보고서 형식의 장황한 문장


10. 하지만 강사 모방에 필요한 정보는 절대 제거하지 마라.

특히 아래는 최대한 보존한다.

- Trigger
- Action
- 설명 방식
- 강조 방식
- 패턴화 방식
- 자주 사용하는 표현
- 대표 발화


==================================================
출력 형식
==================================================

반드시 JSON만 출력한다.

Markdown 코드 블록을 사용하지 마라.

아래 구조를 따른다.

{
  "global_problem_solving": [
    {
      "id": "G-P1",
      "name": "",
      "scope": "global",
      "topic": null,
      "trigger": "",
      "action": "",
      "teaching_behavior": "",
      "preferred_phrases": [],
      "examples": [],
      "related_policies": [],
      "confidence": "high"
    }
  ],

  "global_teaching": [
    {
      "id": "G-T1",
      "name": "",
      "scope": "global",
      "topic": null,
      "trigger": "",
      "action": "",
      "teaching_behavior": "",
      "preferred_phrases": [],
      "examples": [],
      "related_policies": [],
      "confidence": "high"
    }
  ],

  "local_problem_solving": [
    {
      "id": "L-P1",
      "name": "",
      "scope": "local",
      "topic": "",
      "trigger": "",
      "action": "",
      "teaching_behavior": "",
      "preferred_phrases": [],
      "examples": [],
      "related_policies": [],
      "confidence": "high"
    }
  ],

  "local_teaching": [
    {
      "id": "L-T1",
      "name": "",
      "scope": "local",
      "topic": "",
      "trigger": "",
      "action": "",
      "teaching_behavior": "",
      "preferred_phrases": [],
      "examples": [],
      "related_policies": [],
      "confidence": "high"
    }
  ],

  "uncertain": []
}


==================================================
중요
==================================================

이 JSON은 사람이 읽기 위한 보고서가 아니라
새로운 문제를 해결하는 LLM의 입력으로 사용할 Representation이다.

따라서 짧고 명확해야 하지만,
강사의 세밀한 문제 해결 습관과 설명 특성을 복원하는 데 필요한 정보는 유지해야 한다.


==================================================
상세 Teacher Policy Representation
==================================================
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
        contents=[
            prompt,
            policy_text
        ]
    )

    return response.text


def save_json(raw_result: str):

    output_dir = ROOT / "data" / "policy"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "teacher_policy_compact.json"

    # Gemini가 혹시 ```json ... ``` 형태로 반환했을 경우 제거
    cleaned = raw_result.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0].strip()

    try:
        data = json.loads(cleaned)

    except json.JSONDecodeError as e:
        print("JSON parsing 실패")
        print(e)

        # 원본 결과를 디버깅용으로 저장
        debug_path = output_dir / "teacher_policy_compact_raw.txt"
        debug_path.write_text(
            raw_result,
            encoding="utf-8"
        )

        print(f"Raw output saved to: {debug_path}")
        return

    output_path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(f"Saved to: {output_path}")


if __name__ == "__main__":

    policy_text = load_teacher_policy()

    print("Compressing teacher policy...")

    result = compress_policy(policy_text)

    print(result)

    save_json(result)
