"""Small local-media helpers shared by SoLiT pipelines."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path


def _duration_seconds(video_path: Path) -> float:
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe를 찾을 수 없습니다. ffmpeg를 설치해 주세요.")
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def extract_board_frames(video_path, output_dir, max_frames=12):
    """Extract up to ``max_frames`` evenly spaced JPEG frames from a local video."""
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    if not video_path.is_file():
        raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")
    if max_frames < 1:
        raise ValueError("max_frames는 1 이상이어야 합니다.")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg를 찾을 수 없습니다. ffmpeg를 설치해 주세요.")

    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame_%03d.jpg"
    if any(output_dir.glob("frame_*.jpg")):
        raise FileExistsError(
            f"프레임 파일이 이미 있습니다. 비어 있는 폴더를 지정해 주세요: {output_dir}"
        )

    duration = _duration_seconds(video_path)
    interval = max(duration / max_frames, 0.1)
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video_path),
            "-vf", f"fps=1/{interval:.4f},scale='min(1280,iw)':-2",
            "-frames:v", str(max_frames),
            "-q:v", "3", "-n", str(pattern),
        ],
        check=True,
    )
    frames = sorted(output_dir.glob("frame_*.jpg"))
    if not frames:
        raise RuntimeError("영상에서 프레임을 추출하지 못했습니다.")
    return frames


def main():
    parser = argparse.ArgumentParser(description="강의 영상에서 판서 프레임을 추출합니다.")
    parser.add_argument("video", help="처리할 로컬 영상 파일")
    parser.add_argument("--output-dir", required=True, help="프레임 저장 폴더")
    parser.add_argument("--max-frames", type=int, default=12)
    args = parser.parse_args()
    frames = extract_board_frames(args.video, args.output_dir, args.max_frames)
    print(f"프레임 {len(frames)}개 저장: {args.output_dir}")


if __name__ == "__main__":
    main()
