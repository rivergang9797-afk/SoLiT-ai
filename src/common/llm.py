"""Shared Google GenAI client and request helpers."""
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY를 찾을 수 없습니다. 프로젝트 루트의 .env를 확인해 주세요.")
    return genai.Client(api_key=api_key)


def get_model_name():
    return os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def image_part(image_path):
    image_path = Path(image_path)
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    mime_type = mime_types.get(image_path.suffix.lower())
    if not mime_type:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: {image_path.suffix}")
    if not image_path.is_file():
        raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {image_path}")
    return types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type)


def generate_text(contents):
    client = get_client()
    response = client.models.generate_content(
        model=get_model_name(),
        contents=contents,
    )
    if not response.text or not response.text.strip():
        raise RuntimeError("모델 응답이 비어 있습니다.")
    return response.text.strip()


def generate_json(contents, schema):
    client = get_client()
    response = client.models.generate_content(
        model=get_model_name(),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
        contents=contents,
    )
    if not response.text or not response.text.strip():
        raise RuntimeError("모델 응답이 비어 있습니다.")
    return response.text
