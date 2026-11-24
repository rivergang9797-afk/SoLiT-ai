# Lecture tutor MVP

강의 한 편의 전사와 판서 프레임에서 프로필 초안을 만들고, 수학적 검증 단계에서
조건·표현의 추출 오류를 보완합니다. 문제와 강의 개념의 연결 탐색은 입력을 걸러내지 않습니다.
전역 `teacher_profile`은 불러오지 않습니다.

## 실행 순서

프로젝트 루트에서 실행합니다. 아래 영상은 사용자가 적법하게 확보한 로컬 파일이어야
하며, 이 파이프라인은 YouTube에서 파일을 내려받지 않습니다.

```bash
python -m src.common.stt data/lecture_tutor/lectures/cubic_ratio.mp4 \
  --output data/lecture_tutor/transcripts/cubic_ratio.txt

python -m src.common.media data/lecture_tutor/lectures/cubic_ratio.mp4 \
  --output-dir data/lecture_tutor/frames/cubic_ratio --max-frames 12

python -m src.lecture_tutor.analyze_lecture \
  --transcript data/lecture_tutor/transcripts/cubic_ratio.txt \
  --frames-dir data/lecture_tutor/frames/cubic_ratio \
  --lecture-id cubic_ratio --output data/lecture_tutor/profiles/cubic_ratio.draft.json

python -m src.lecture_tutor.validate_lecture \
  --draft data/lecture_tutor/profiles/cubic_ratio.draft.json \
  --transcript data/lecture_tutor/transcripts/cubic_ratio.txt \
  --frames-dir data/lecture_tutor/frames/cubic_ratio \
  --output data/lecture_tutor/profiles/cubic_ratio.json \
  --report data/lecture_tutor/profiles/cubic_ratio.validation.json

python -m src.lecture_tutor.process_homework
```

위 명령은 `homework` 폴더의 이미지 파일을 `001.png`, `002.png`처럼 번호로 바꾼 뒤,
연결 분석과 해설을 각각 `discoveries/001.json`, `solutions/001.md`에 저장합니다.
새 이미지도 같은 명령으로 처리하며, 기존 번호 다음 번호를 받습니다. 원래 파일명은
`homework/renamed_files.json`에 기록합니다. 이미 해설이 있는 문제는 건너뜁니다.

`.env`에 `GEMINI_API_KEY`가 필요합니다. 필요하면 `GEMINI_MODEL`로 모델명을 바꿀 수
있습니다. `ffmpeg`와 `ffprobe`는 별도로 설치해야 합니다.

검증 단계는 오류로 보이는 관계를 곧바로 삭제하지 않습니다. 가능한 경우 수학적 유도와
전사·판서 맥락으로 조건과 표현을 보완하고, 복원할 수 없는 경우에는 불확실성을 남깁니다.

전체 데이터 디렉터리 구성은 [`data/README.md`](../../data/README.md)를 참고합니다.
