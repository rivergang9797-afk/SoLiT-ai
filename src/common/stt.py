from pathlib import Path
from faster_whisper import WhisperModel
from tqdm import tqdm


class STT:

    def __init__(self,
                 model_name="medium",
                 device="cpu",
                 compute_type="int8"):

        print("Loading Whisper model...")
        self.model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type
        )

    def transcribe_file(self, video_path):
        """Return a plain-text Korean transcript for one local audio/video file."""
        segments, _info = self.model.transcribe(
            str(video_path),
            language="ko",
        )
        return "\n".join(seg.text.strip() for seg in segments if seg.text.strip())

    def transcribe_folder(self,
                          video_dir,
                          output_dir):

        video_dir = Path(video_dir)
        output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        videos = sorted(
            [
                f for f in video_dir.iterdir()
                if f.suffix.lower() in [".mp4", ".mov"]
            ]
        )   

        for video in tqdm(videos):

            output_path = output_dir / (video.stem + ".txt")

            if output_path.exists():
                continue

            text = self.transcribe_file(video)

            output_path.write_text(
                text,
                encoding="utf-8"
            )

        print("Done.")


def main():
    """CLI for transcribing one lecture video using the shared STT utility."""
    import argparse

    parser = argparse.ArgumentParser(description="강의 영상의 음성을 전사합니다.")
    parser.add_argument("video", help="전사할 로컬 영상/오디오 파일")
    parser.add_argument("--output", required=True, help="저장할 .txt 경로")
    parser.add_argument("--model", default="medium", help="faster-whisper 모델")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        parser.error(f"출력 파일이 이미 있습니다: {output_path}")

    transcript = STT(model_name=args.model).transcribe_file(args.video)
    output_path.write_text(transcript + "\n", encoding="utf-8")
    print(f"전사 저장 완료: {output_path}")


if __name__ == "__main__":
    main()
