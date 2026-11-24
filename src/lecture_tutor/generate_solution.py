"""Generate a homework explanation grounded in a lecture profile."""
import argparse
import json
from pathlib import Path

from ..common.llm import generate_text, image_part


PROMPT = """너는 고등학교 수학 문제의 풀이를 설명하는 튜터다.
강의 프로필과 연결 탐색 결과는 참고 자료다. 학생이 올린 문제를 정확히 풀고, 강의 내용과
연결되는 부분이 있으면 해당 개념과 적용 조건을 풀이에 연결해 설명한다.

규칙:
- 먼저 문제의 조건과 구할 것을 정확히 읽고 풀이한다.
- 탐색 결과가 clear 또는 possible이면, 문제의 어떤 조건이 강의의 어떤 개념과 연결되는지 확인해 풀이에 반영한다.
- 탐색 결과가 unclear이면 연결을 억지로 만들지 않는다. 그래도 문제 자체는 끝까지 풀고, 필요한 경우에만 연결의 불확실성을 짧게 알린다.
- 탐색 결과를 문제 풀이 여부를 결정하는 필터로 사용하지 않는다.
- 프로필에 없는 강사 말투나 판서 행동을 흉내 내지 않는다. teacher_profile도 사용하지 않는다.
- 계산과 논리를 검토하고, 최종 답을 명확히 표시한다. 한국어로 작성한다.
"""


def generate_solution(profile_path, discovery_path, problem_path, output_path):
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(f"출력 파일이 이미 있습니다: {output_path}")
    profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    discovery = json.loads(Path(discovery_path).read_text(encoding="utf-8"))
    contents = [
        PROMPT,
        "[강의 프로필]\n" + json.dumps(profile, ensure_ascii=False, indent=2),
        "[강의 개념 연결 탐색 결과]\n" + json.dumps(discovery, ensure_ascii=False, indent=2),
        "[학생의 숙제 문제 이미지]",
        image_part(problem_path),
    ]
    solution = generate_text(contents)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(solution + "\n", encoding="utf-8")
    return solution


def main():
    parser = argparse.ArgumentParser(description="강의 내용에 연결해 숙제 해설을 생성합니다.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--discovery", required=True)
    parser.add_argument("--problem", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    generate_solution(args.profile, args.discovery, args.problem, args.output)
    print(f"해설 저장 완료: {args.output}")


if __name__ == "__main__":
    main()
