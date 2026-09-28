import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

client = genai.Client(api_key=GEMINI_API_KEY)


def _parse_json_response(text: str) -> dict:
    """
    Gemini sometimes wraps JSON in markdown code fences.
    This removes them before parsing.
    """
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]

    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return json.loads(cleaned.strip())


def classify_intent(text: str) -> dict:
    prompt = f"""
You are the intent router for a WhatsApp personal memory assistant.

The assistant is used as a place where users casually send things
they want to remember later.

Classify the user's message into exactly one of these intents:

SAVE
- The user is sending new information or content.
- The message does NOT need to explicitly say "save this".
- Standalone content should normally be classified as SAVE.
- Examples:
  - a recipe
  - an address
  - a recommendation
  - notes
  - information copied from somewhere
  - a URL

SEARCH
- The user is asking to find or return something they previously stored.
- Examples:
  - "find the carrot cake recipe"
  - "send me the restaurant I saved"
  - "where is the document I sent last week?"

Important:
If the message is standalone content and is not clearly asking to retrieve
previously saved information, classify it as SAVE.

Return JSON only:

{{
  "intent": "SAVE" or "SEARCH",
  "search_query": null or "..."
}}

Rules:
- For SAVE, search_query must be null.
- For SEARCH, search_query should be a short description of the item
  the user wants to retrieve.
- Preserve important identifying details in the search query.
- Do not include markdown or explanations.

User message:
{text}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    return _parse_json_response(response.text)


def enrich_text_item(text: str) -> dict:
    prompt = f"""
You organize items saved in a personal/shared memory application.

Analyze the following saved text and generate useful metadata.

Choose exactly one category from:
- Recipe
- Travel
- Document
- Purchase
- Recommendation
- Finance
- Other

Return JSON only in this format:

{{
  "title": "...",
  "category": "...",
  "tags": ["...", "..."],
  "summary": "..."
}}

Rules:
- The title should be short and useful for finding the item later.
- Infer what the content is about even if the user did not provide a title.
- Do not invent specific facts that are not supported by the content.
- Use 2-5 useful tags.
- Keep the title, tags and summary in the same language as the saved content.
- The category must remain one of the English categories listed above.
- Do not include markdown or explanations.

Saved content:
{text}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    return _parse_json_response(response.text)


def fallback_classify_intent(text: str) -> dict:
    """
    Lightweight fallback when Gemini intent classification
    is unavailable.
    """

    normalized = text.strip()
    lowered = normalized.lower()

    search_prefixes = [
        "תמצא",
        "תמצאי",
        "תביא",
        "תביאי",
        "חפש",
        "חפשי",
        "שלח לי",
        "שלחי לי",
        "תשלח",
        "תשלחי",
        "איפה",
        "find ",
        "search ",
        "show me",
        "send me",
        "get me",
    ]

    question_prefixes = [
        "כמה",
        "מתי",
        "איך",
        "למה",
        "מי",
        "איזה",
        "איזו",
        "אילו",
        "האם",
        "מה",
        "באיזה",
        "באיזו",
        "what",
        "how",
        "when",
        "why",
        "who",
        "which",
    ]

    is_search_command = any(
        lowered.startswith(prefix)
        for prefix in search_prefixes
    )

    is_question = (
        "?" in normalized
        or any(
            lowered.startswith(prefix)
            for prefix in question_prefixes
        )
    )

    if is_search_command or is_question:
        return {
            "intent": "SEARCH",
            "search_query": normalized,
        }

    return {
        "intent": "SAVE",
        "search_query": None,
    }