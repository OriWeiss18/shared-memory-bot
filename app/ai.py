import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

client = genai.Client(api_key=GEMINI_API_KEY)


def classify_intent(text: str) -> dict:
    prompt = f"""
You are the intent router for a WhatsApp personal memory assistant.

Classify the user's message into exactly one of these intents:

SAVE
- The user is sending information they want to store.

SEARCH
- The user is asking to find or return something they previously stored.

Return JSON only in this exact format:

{{
  "intent": "SAVE" or "SEARCH",
  "search_query": null or "..."
}}

Rules:
- If intent is SAVE, search_query must be null.
- If intent is SEARCH, rewrite the request as a short search query describing the item they want to find.
- Do not include markdown or explanation.

User message:
{text}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    return json.loads(response.text)