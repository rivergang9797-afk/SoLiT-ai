"""Number homework images and generate their lecture-grounded solutions."""
import json
import re
from pathlib import Path

from .discover_problem import discover_problem
from .generate_solution import generate_solution


ROOT = Path(__file__).resolve().parents[2]
HOMEWORK_DIR = ROOT / "data/lecture_tutor/homework"
PROFILE_PATH = ROOT / "data/lecture_tutor/profiles/cubic_ratio.json"
DISCOVERY_DIR = ROOT / "data/lecture_tutor/discoveries"
SOLUTION_DIR = ROOT / "data/lecture_tutor/solutions"
MANIFEST_PATH = HOMEWORK_DIR / "renamed_files.json"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _number_homework_images():
    images = sorted(
        (path for path in HOMEWORK_DIR.iterdir()
         if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: path.name,
    )
    numbered = [
        int(match.group(1))
        for path in images
        if (match := re.fullmatch(r"(\d{3,})", path.stem))
    ]
    next_number = max(numbered, default=0) + 1

    manifest = {}
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    for image in images:
        if re.fullmatch(r"\d{3,}", image.stem):
            continue
        target = image.with_name(f"{next_number:03d}{image.suffix.lower()}")
        if target.exists():
            raise FileExistsError(f"번호 파일이 이미 있습니다: {target}")
        image.rename(target)
        manifest[target.name] = image.name
        print(f"이름 변경: {image.name} → {target.name}")
        next_number += 1

    if manifest:
        MANIFEST_PATH.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return sorted(
        (path for path in HOMEWORK_DIR.iterdir()
         if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: (0, int(path.stem)) if path.stem.isdigit() else (1, path.name),
    )


def process_homework():
    if not PROFILE_PATH.is_file():
        raise FileNotFoundError(f"강의 프로필이 없습니다: {PROFILE_PATH}")
    if not HOMEWORK_DIR.is_dir():
        raise FileNotFoundError(f"숙제 폴더가 없습니다: {HOMEWORK_DIR}")

    images = _number_homework_images()
    if not images:
        print(f"처리할 이미지가 없습니다: {HOMEWORK_DIR}")
        return

    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    SOLUTION_DIR.mkdir(parents=True, exist_ok=True)
    for image in images:
        problem_id = image.stem
        discovery_path = DISCOVERY_DIR / f"{problem_id}.json"
        solution_path = SOLUTION_DIR / f"{problem_id}.md"

        if solution_path.exists():
            print(f"이미 처리됨: {image.name}")
            continue

        if not discovery_path.exists():
            discover_problem(PROFILE_PATH, image, discovery_path)
            print(f"연결 분석 저장: {discovery_path.relative_to(ROOT)}")

        generate_solution(PROFILE_PATH, discovery_path, image, solution_path)
        print(f"해설 저장: {solution_path.relative_to(ROOT)}")


if __name__ == "__main__":
    process_homework()
