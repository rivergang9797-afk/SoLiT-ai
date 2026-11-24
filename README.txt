             Teacher Solution Videos
                       +
                problem images
                       │
              ┌────────┴────────┐
              ↓                 ↓
        Reasoning Policy   Presentation Policy
              │                 │
              ↓                 ↓
        무엇을 풀 것인가    어떻게 보여줄 것인가
              │                 │
              └────────┬────────┘
                       ↓
               Teaching Script
                       ↓
          ┌────────────┼────────────┐
          ↓            ↓            ↓
        Speech       Writing       Visual
         TTS          수식/판서      그래프/강조
          └────────────┼────────────┘
                       ↓
                  학생 화면

============================================================
프로필 파이프라인 구분
============================================================

lecture_profile은 한 강의의 개념·공식·적용 조건을 추출해 관련 숙제 해설에 사용한다.
이번 MVP의 풀이 생성에는 teacher_profile을 불러오지 않는다.
teacher_profile은 여러 문제풀이 영상에서 강사의 재사용 가능한 풀이·설명 정책을 추출한다.

공통 음성·미디어·LLM 처리는 src/common/에 둔다. 강의 기반 숙제 해설 파이프라인은
src/lecture_tutor/에, 강사 풀이 정책 파이프라인은 src/teacher_profile/에 둔다.
lecture_profile은 강의에서 추출한 지식 데이터의 구조를 정의한다.


============================================================
버전 이력 및 실행 방법
============================================================

버전은 분석(analyze), 정책 추출(discover), 해설 생성(generate)을 구분해 기록한다.
V5는 기존 analysis/v4를 입력으로 사용하는 discover 변경 버전이다.
분석을 V5로 다시 수행했다는 의미가 아니며, 생성 프롬프트도 이번 변경에서 수정하지 않았다.

[V1 — 기존 정책 기준선]
- 분석 자료: data/teacher_profile/analysis/v1/
- 정책: data/teacher_profile/profiles/teacher_policy.md
- 생성 결과: data/teacher_profile/generations/testXXX/policyV1.txt
- 풀이·교수 행동을 Trigger → Action 형태로 통합한 기존 비교 기준선.
- 현재 보관된 V1 생성 결과는 사용자가 제공한 과거 터미널 출력에서 복구했다.

[V2 / V3 — 분석 개선 중간 버전]
- 자료: data/teacher_profile/analysis/v2/, data/teacher_profile/analysis/v3/
- 문항별 분석을 개선하는 과정의 중간 산출물이다.
- 현재 파일만으로 두 버전의 정확한 변경 내역 전체를 확정할 수 없어 상세 내용은 미기록.
- 별도의 teacher_policy_v2.md / teacher_policy_v3.md와 policyV2.txt / policyV3.txt는 현재 없다.

[V4 — 교수 행동을 구조화한 분석 및 정책]
- 분석: data/teacher_profile/analysis/v4/*.txt 및 data/teacher_profile/analysis/v4/records/*.json (현재 12문제)
- 정책: data/teacher_profile/profiles/teacher_policy_v4.md
- 생성 결과: data/teacher_profile/generations/testXXX/policyV4.txt
- T01~T12 교수 행동 항목과 OTHER를 사용해 행동을 관찰한다.
- 근거 전사 줄 번호, 설명 상황·시점·분량, 선택 행동과 이유, 비관찰·불확실성을 기록한다.
- JSON 관찰에서 코드로 보고서와 Step 단위 집계를 구성한다.
- discover는 반복 행동, 적용 조건, 반례, 문제 단위 빈도, 불확실 후보를 통합한다.
- 확인된 한계: 정책 통합 시 설명 시점·강도와 전략 전환의 조건이 충분히 보존되지 않았다.
  일부 문제의 회고나 짧은 목표 언급이 넓은 실행 규칙으로 바뀌었고,
  생성에서는 과도한 회고·목표 선언·차함수 접근이 나타났다.
- 상세 점검: docs/policy_pipeline_audit_20261110.md

[V5 — 맥락을 보존하는 정책 압축 / 2026-11-10]
- 변경 파일: src/discover.py
- 입력: 기존 data/teacher_profile/analysis/v4/ (analyze 결과 재생성 불필요)
- 상세 정책: data/teacher_profile/profiles/teacher_policy_v5_detailed.md
- 실행용 정책: data/teacher_profile/profiles/teacher_policy_v5.md
- 생성 시 저장 이름: data/teacher_profile/generations/testXXX/policyV5.txt

변경 목적:
모든 분석을 생성 입력에 넣는 대신, 행동 선택과 설명 강도를 바꾸는 정보를 남겨 압축한다.
개별 문제의 수식·계산·중복 인용은 줄이되, 최초 접근과 전략 전환의 조건을 구분한다.

변경 내용:
1. 출력 분리
   상세 정책에는 근거·관찰 맥락·비관찰·시점·분량·적용 경계를 보관하고,
   실행용에는 조건·행동·설명 조절·경계·불확실성을 압축한다.
2. 과잉 일반화 제한
   문제에서 한 번 관찰된 행동을 모든 단계의 필수 행동으로 바꾸지 않는다.
   조건이 다른 사례를 지지 문제 수를 늘리려고 합치지 않는다.
   회고 비관찰 사례도 검토하며, 문제 단위 빈도를 장면별 실행률로 해석하지 않는다.
3. 설명 조절 정보 보존
   짧은 언급 / 연결 설명 / 상세 전개와 실행 시점을 남긴다.
   강도 선택 기준이 없으면 미확인으로 표시하며 난이도 규칙을 추측하지 않는다.
4. 불확실성 유지
   확정 정책과 후보를 구분하며, 후보를 강사의 필수 루틴으로 가르치지 않게 한다.
   Unknown을 제약이 없는 실행 권한으로 취급하지 않는다.
5. 압축 예산과 검증
   실행용 기본 한도는 공백 포함 12,000자이며 --max-runtime-chars로 조정한다.
   이는 토큰 수나 전체 컨텍스트 한도 보장이 아니며, 최적값으로 검증된 값도 아니다.
   초과·출력 구분자 오류·상세/실행용 정책 ID 불일치 시 최종 정책 저장을 중단한다.
   형식 검증은 의미 보존의 정확성을 보장하지 않는다.
6. 기록 보존
   입력 분석 사본·모델 응답·설정을 data/teacher_profile/runs/discovery/에 저장한다.
   기존 정책은 덮어쓰지 않는다. 재실행할 때는 다른 --output 이름을 지정한다.

검증 상태:
- 외부 API 호출 없는 자동 검사 8개 통과 (출력 분리·예산·ID·기존 파일 보호 등).
- V5 정책의 실제 Gemini 추출 및 V4 대비 생성 품질 비교는 아직 수행하지 않았다.
- generate의 기본 정책은 V4로 유지했다. V5 평가에는 --policy를 명시한다.

실행:
  source .venv/bin/activate
  python -m src.teacher_profile.discover

V5 정책 생성 후 test005만 평가:
  python -m src.teacher_profile.generate --policy-only --ids test005 --policy data/teacher_profile/profiles/teacher_policy_v5.md

V5 정책 생성 후 전체 테스트 평가:
  python -m src.teacher_profile.generate --policy-only --policy data/teacher_profile/profiles/teacher_policy_v5.md

예산을 변경하고 별도 이름으로 다시 추출:
  python -m src.teacher_profile.discover --max-runtime-chars 16000 --output data/teacher_profile/profiles/teacher_policy_v5_budget16000.md

위처럼 버전 접미사가 없는 별도 이름을 생성에 사용할 때는 버전을 명시한다.
같은 V5 이름을 사용하면 기존 policyV5.txt는 .history/에 백업되고 새 결과가 대표 파일이 된다.
서로 다른 실험을 동시에 비교하려면 기존 결과를 별도 보관하고 실험 조건을 함께 기록한다.
  python -m src.teacher_profile.generate --policy-only --policy data/teacher_profile/profiles/teacher_policy_v5_budget16000.md --policy-version V5

[공통 생성·보관 방식 / 2026-11-10 정리]
- 문항별 폴더: baseline.txt, fewshot.txt, policyV1.txt, policyV4.txt, policyV5.txt 등.
- policyV5.txt는 실제 생성한 이후에 생긴다.
- --policy-only: baseline과 few-shot을 다시 생성하지 않는다.
- --ids test001 test005: 선택한 문항만 생성한다.
- 생성 내용은 터미널에 출력하지 않고 파일로 저장한다. 진행 상황·저장 경로만 출력한다.
- teacher_policy_v숫자.md는 파일명에서 버전을 판별한다. teacher_policy.md는 V1이다.
- 같은 파일을 재생성하면 이전 파일을 문항 폴더의 .history/에 백업한다.
- 정리 전 생성 자료와 복구 원문은 data/teacher_profile/archives/generations/에 보관한다.


[분석 결과 폴더 정리 / 2026-11-13]
- data/teacher_profile/analysis/ 아래에 v1/, v2/, v3/, v4/를 모았다.
- 기존 analysis의 문항은 v1/, analysis_v2~v4는 각각 v2~v4/로 이동했다.
- v4/records/의 JSON 원본도 함께 보존했다. 파일 내용은 변경하지 않았다.
- analyze 기본 출력과 discover 기본 입력은 data/teacher_profile/analysis/v4/이다.
- V5는 discover 변경 버전이므로 별도 analysis/v5/를 만들지 않는다.

[V5 discover 프롬프트 재작성 / 2026-11-13]
- 이전 V5 프롬프트의 현재 문항·특정 풀이 유형·개별 실패 사례를 겨냥한 예시와 지시를 제거했다.
- 특정 교수 행동을 미리 필수 정책으로 지정하지 않고 관찰에서 정책을 발견하도록 한다.
- 통합 기준을 목표·상황·선택 조건·행동·설명 기능·실행 방식으로 명시했다.
- 표면적 행동이 비슷해도 선택 조건이나 설명 기능이 다르면 합치지 않는다.
- 통합 전 관찰 기능과 통합 후 정책을 대조하고, 정책화하지 못한 내용은 보류 목록에 남긴다.
- 행동별 반복성과 전체 시퀀스 반복성을 분리하고 각 문항의 전체 순서 근거를 요구한다.
- 시점·분량의 차이를 단일값으로 통일하지 않으며, 그 선택 기준이 미확인이면 명시한다.
- 관찰·해석·가설과 비관찰·명시적 미수행·판단 불가를 구분한다.
- 문제 단위 빈도를 장면별 실행 의무로 바꾸지 않고, 적용 범위·확신을 근거에 제한한다.
- 상세/실행용 출력과 기본 12,000자 예산은 유지한다.
- 반복성 최소 3문항은 기존 프로젝트 기준으로 유지하되 통계적 보증이 아님을 명시했다.
- build_discovery_prompt()로 프롬프트 구성을 분리하고 실제 요청 프롬프트를 실행 기록에 저장한다.
- 이름 형식이 다른 시퀀스·후보 ID도 상세/실행용 일치 검사에 포함하도록 보완했다.
- 외부 API 호출 없는 검사 9개 통과. 의미 보존·생성 품질은 실제 추출 후 평가해야 한다.
- 기존 teacher_policy_v5.md 및 _detailed.md는 이전 프롬프트의 산출물이며 변경하지 않았다.
- 같은 V5 내 프롬프트 개정이다. 비교를 위해 재추출 결과는 다른 --output 경로에 저장한다.
  python -m src.teacher_profile.discover --output data/teacher_profile/profiles/teacher_policy_v5_revised.md

[V5 설명 분량 규칙 보완 / 2026-11-13]
- 설명 분량을 문장 수의 목표·범위·상한으로 지정하지 않도록 명시했다.
- 관찰된 정성적 분량을 유지하며 문장 수·시간·발화 횟수로 환산하지 않는다.
- STT 줄 수를 문장 수나 시간으로 취급하지 않고, 자료에 없는 수치를 만들어내지 않는다.
- 원문에 실제 측정이 있어도 상세 문서의 관찰 근거와 생성 실행 지시를 구분한다.
- 기존 정책 산출물은 변경하지 않았으며, 다음 discover 실행부터 적용된다.

[V5 정책 근거 검증 단계 추가 / 2026-11-13]
- src/policy_validation.py를 추가하고 discover에 추출 후 근거 검토 단계를 연결했다.
- 정상적인 신규 추출은 모델 요청 2회(추출 1회 + 검토 1회)다. 추출의 기존 503 재시도는 별도다.
- 상세/실행용 정책의 필드별 주장을 문서·정책·범주별 ID로 나누어 전부 검토 대상으로 만든다.
- 별도 Gemini 요청은 원래 analysis와 정책을 비교하며, 정책을 고치거나 새로운 교수법을 만들지 않는다.
- 판정: 지지됨 / 부분 지지 / 근거 부족 / 근거와 충돌. 각 항목에 이유와 원문 근거를 남긴다.
- 문서 전체의 관찰 기능 누락·과도한 통합 등도 별도 coverage_findings로 기록한다.
- 코드는 검토 대상의 누락·중복·추가, 참조 문항·Step 존재, Step 선후 순서, 인용 원문 일치를 검증한다.
- 이 검사는 인용의 존재와 순서를 확인한다. 그 인용이 주장을 의미적으로 뒷받침하는지는 모델 판단이다.
- 기존 실행 기록 폴더에 draft_detailed.md, draft_runtime.md, validation_prompt.txt,
  validation_input.json, validation_raw_response.txt, validation.json, validation.md를 저장한다.
- 부분 지지·근거 부족·충돌 또는 문서 전체 미해결 항목이 있으면 최종 정책 저장을 보류한다.
  검토 요청 실패·불완전 응답·잘못된 근거도 저장을 막고 초안과 오류 기록을 보존한다.
- 검토가 통과해도 정책 품질이 보증되는 것은 아니다. 같은 모델의 별도 요청이므로 공통 오류가 가능하다.
- 자동 검사 20개 통과. 모두 가짜 모델 응답을 이용한 동작 검사이며 실제 의미 판정 품질 검증은 미수행.

이미 만든 정책을 재추출 없이 검증만 수행 (모델 검토 요청 1회):
  python -m src.teacher_profile.discover --verify-existing data/teacher_profile/profiles/teacher_policy_v5_revised.md

새 정책 추출 후 검증 (기존 파일을 보존하려면 새 출력 이름 사용):
  python -m src.teacher_profile.discover --output data/teacher_profile/profiles/teacher_policy_v5_checked.md

검토만 수행하는 모드에서는 기존 정책 파일을 수정하거나 삭제하지 않는다.
보고서는 터미널에 표시되는 data/teacher_profile/runs/discovery/<실행>/validation.md에서 확인한다.

[V5 검토 응답 불일치 복구 / 2026-11-13]
- 실제 검토 요청 224개에 대해 231개 응답이 반환돼 엄격한 ID 검사에서 중단된 사례를 수정했다.
- 요청 외 항목은 integrity.extra_assessments에 분리 보관하고 요청한 항목의 판정을 유지한다.
- 누락·중복·잘못된 참조·인용 불일치는 통과시키지 않고 코드 미검증(근거 부족)으로 기록한다.
  기존 모델 판정은 model_assessments에 보관하며 원본 응답 파일을 변경하지 않는다.
- 다음 요청은 JSON schema로 claim ID와 근거 ID를 제한한다.
  모델이 인용문을 재작성하는 대신 근거 ID를 선택하고 코드가 원문을 직접 가져온다.
  참조된 원문이 실제 주장을 지지하는지는 여전히 모델 판단으로 별도 검토가 필요하다.
- 정책 제목에만 존재하는 주장도 검토 대상으로 포함했다.
- 저장된 요청의 analysis 스냅샷과 응답으로 API 재호출 없이 보고서를 복구할 수 있다.
  python -m src.teacher_profile.discover --recover-review data/teacher_profile/runs/discovery/20261113_141143_0r5xeri0
- 복구 후에도 미해결·미검증 항목이 있으면 정책 확정은 보류한다.
  이전 validation_error.txt는 최초 실패 기록이며 복구 결과는 validation.json/md에서 확인한다.
- 실제 실패 응답으로 보고서 복구 확인: 요청 224, 원문 참조 검증 통과 130, 미검증 94, 요청 외 7.
  이는 의미적으로 옳은 정책 130개를 확인했다는 뜻이 아니다. 실제 응답은 모든 항목을 지지됨으로
  판정했으므로, 의미 판정의 신뢰성 역시 별도로 검토해야 한다.
- 누락·중복·인용 불일치·근거 ID 복원·기존 응답 복구 등의 동작 검사를 통과했다.

[정책 검토 대상 조정 / 2026-11-18]
- 정책 제목·이름·ID 표기는 별도 의미 검토 항목에서 제외한다.
- 본문에 명시된 확정/후보 상태, 유형, 적용 범위와 주제는 계속 검토한다.

[규칙별 채택 및 제한된 정책 저장 / 2026-11-20]
- 전체 주장 통과 여부(validation.passed)와 최종 정책 저장 가능 여부를 분리했다.
- 상세/실행용 양쪽에서 해당 규칙의 모든 주장이 지지됨인 규칙만 채택한다.
- 부분 지지·근거 부족·충돌·누락·중복·근거 참조 미검증은 해당 규칙 전체를 제외한다.
- 제외된 규칙을 참조하는 시퀀스/규칙도 연쇄 제외한다. 조건만 제거하고 행동을 남기지 않는다.
- 부분 지지 규칙의 자동 수정·재검토는 구현하지 않았다. 원문 초안과 판정은 보존한다.
- 문서 전체 지적에 명시된 규칙 ID는 제외한다. 특정할 수 없는 문서 전체 충돌이나
  문서 전체 검토 형식 오류는 저장을 보류한다. 나머지 전체 지적은 제한 사항으로 보고한다.
- 지지되지 않은 문서 공통 원칙은 고정된 최소 운영 안내로 대체한다.
- 채택 규칙이 없으면 저장하지 않는다. API 실패/최상위 응답 오류도 저장하지 않는다.
- selection.json/md에 채택 ID·제외 이유·문서 전체 주의 사항·저장 가능 여부를 기록한다.
- --verify-existing은 채택 보고서만 추가하며 기존 정책 파일을 수정하지 않는다.
- 기존 출력 덮어쓰기 금지는 유지한다. 새 결과는 --output으로 별도 경로에 저장한다.
- 검토 전체 통과와 실제 재현 성능은 별개다. 생성 품질 검증은 아직 수행하지 않았다.
- 외부 API 호출 없는 자동 검사 29개 통과(일부 규칙 탈락 시 나머지 저장 포함).
