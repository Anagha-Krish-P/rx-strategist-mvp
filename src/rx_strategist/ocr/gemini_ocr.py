from pathlib import Path
from typing import Union

from google import genai
from google.genai import types

OCR_PROMPT = """
You are a prescription OCR system.

Your job is ONLY to transcribe the visible text from the prescription image.

Do NOT decide whether a medication is appropriate.
Do NOT provide medical advice.
Do NOT invent missing patient information.
Do NOT extract structured JSON.
Do NOT add commentary, headings, or markdown.

Return only the transcribed prescription text.
If a word is unreadable, write [illegible].
"""

MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

ImageInput = Union[str, Path, bytes]


def _mime_type_from_path(path: Path) -> str:
    mime_type = MIME_TYPES.get(path.suffix.lower())
    if not mime_type:
        supported = ", ".join(sorted(MIME_TYPES))
        raise ValueError(
            f"Unsupported image type {path.suffix!r}. Supported types: {supported}."
        )
    return mime_type


class GeminiPrescriptionOCR:
    def __init__(self, api_key: str, model: str = "models/gemini-3.5-flash-lite"):
        if not api_key:
            raise ValueError("A Gemini API key is required.")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def ocr_image(
        self,
        image: ImageInput,
        mime_type: str = None,
    ) -> str:
        image_bytes, resolved_mime_type = self._load_image(image, mime_type)
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                OCR_PROMPT,
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=resolved_mime_type,
                ),
            ],
        )
        if not response.text:
            raise ValueError("OCR returned no text.")
        return response.text.strip()

    def _load_image(self, image: ImageInput, mime_type: str = None):
        if isinstance(image, bytes):
            if not mime_type:
                raise ValueError("mime_type is required when passing image bytes.")
            return image, mime_type

        path = Path(image)
        if not path.is_file():
            raise FileNotFoundError(f"Image file not found: {path}")

        resolved_mime_type = mime_type or _mime_type_from_path(path)
        return path.read_bytes(), resolved_mime_type
