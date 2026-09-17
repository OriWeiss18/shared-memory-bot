import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_item_embedding(
    text: str,
    title: str | None = None,
) -> list[float]:
    result = client.models.embed_content(
        model="gemini-embedding-2",
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
            title=title,
        ),
    )

    return result.embeddings[0].values


def generate_query_embedding(query: str) -> list[float]:
    result = client.models.embed_content(
        model="gemini-embedding-2",
        contents=query,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
    )

    return result.embeddings[0].values

def build_item_search_text(
    title: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
    content: str | None = None,
    original_text: str | None = None,
) -> str:
    parts = []

    if title:
        parts.append(f"Title: {title}")

    if category:
        parts.append(f"Category: {category}")

    if tags:
        parts.append(f"Tags: {', '.join(tags)}")

    if summary:
        parts.append(f"Summary: {summary}")

    body = content if content is not None else original_text

    if body:
        parts.append(f"Content: {body}")

    return "\n".join(parts)