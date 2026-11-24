"""Transcribe worked-solution videos for the teacher-profile pipeline."""
import argparse
from pathlib import Path

from ..common.stt import STT


ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(
        description="문제풀이 영상의 음성을 전사합니다."
    )
    parser.add_argument("--video-dir", default="data/teacher_profile/videos")
    parser.add_argument("--output-dir", default="data/teacher_profile/transcripts")
    parser.add_argument("--model", default="medium")
    args = parser.parse_args()

    video_dir = Path(args.video_dir)
    output_dir = Path(args.output_dir)
    if not video_dir.is_absolute():
        video_dir = ROOT / video_dir
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir

    STT(model_name=args.model).transcribe_folder(video_dir, output_dir)


if __name__ == "__main__":
    main()
