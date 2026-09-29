import mimetypes
import time
from pathlib import Path

from google import genai
from google.genai import types

from app.ai import _parse_json_response
from app.ai import GEMINI_API_KEY


SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

client = genai.Client(api_key=GEMINI_API_KEY)


def analyze_image_bytes(
    image_bytes: bytes,
    mime_type: str,
) -> dict:
    """
    Analyze an image and return searchable metadata.

    This function is independent of WhatsApp and Supabase.
    It can later receive image bytes from WhatsApp, the web app,
    or any other source.
    """

    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise ValueError(
            f"Unsupported image type: {mime_type}"
        )

    prompt = """
You organize items saved in a personal/shared memory application.

Analyze the supplied image and return useful information that will
allow the user to find this image later using semantic search.

Choose exactly one category from:
- Recipe
- Travel
- Document
- Purchase
- Recommendation
- Finance
- Other

Return JSON only in this exact structure:

{
  "title": "...",
  "category": "...",
  "tags": ["...", "..."],
  "summary": "...",
  "description": "...",
  "extracted_text": null
}

Rules:
- title should be short and useful for finding the image later.
- summary should briefly explain why this image may be useful.
- description should describe important visible objects, context,
  places, documents, products, people, or other useful details.
- extracted_text should contain useful text visibly present in the
  image.
- If there is no useful visible text, extracted_text must be null.
- Do not invent text or facts that are not visible or strongly
  supported by the image.
- Use 2-5 useful tags.
- category must be one of the English categories listed above.
- When the image clearly contains text in a particular language,
  use that language for title, tags, summary, and description.
- Do not include markdown or explanations.
"""

    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type,
                    ),
                    prompt,
                ],
            )

            return _parse_json_response(response.text)

        except Exception as exc:
            error_text = str(exc)

            is_temporary_error = (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "high demand" in error_text.lower()
            )

            if not is_temporary_error or attempt == max_attempts - 1:
                raise

            wait_seconds = 2 ** (attempt + 1)

            print(
                f"Gemini temporarily unavailable. "
                f"Retrying in {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)


def analyze_image_file(path: str) -> dict:
    """
    Development helper for testing an image directly from the computer.
    """

    image_path = Path(path)

    if not image_path.is_file():
        raise FileNotFoundError(
            f"Image file not found: {image_path}"
        )

    mime_type, _ = mimetypes.guess_type(image_path.name)

    if mime_type is None:
        raise ValueError(
            "Could not determine image MIME type"
        )

    return analyze_image_bytes(
        image_bytes=image_path.read_bytes(),
        mime_type=mime_type,
    )