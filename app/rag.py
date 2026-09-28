from app.ai import client


def build_item_context(item: dict) -> str:
    """
    Convert a saved item into text that can be used
    as context for a RAG answer.
    """

    source_type = item.get("source_type")

    parts = [
        f"Title: {item.get('title') or ''}",
        f"Category: {item.get('category') or ''}",
        f"Summary: {item.get('summary') or ''}",
    ]

    tags = item.get("tags") or []

    if tags:
        parts.append(
            f"Tags: {', '.join(tags)}"
        )

    if source_type == "text":
        original_text = item.get("original_text")

        if original_text:
            parts.append(
                f"Content:\n{original_text}"
            )

    elif source_type == "url":
        extracted_text = item.get("extracted_text")

        if extracted_text:
            parts.append(
                f"Page content:\n{extracted_text}"
            )

        original_url = item.get("original_url")

        if original_url:
            parts.append(
                f"URL: {original_url}"
            )

    elif source_type == "image":
        description = item.get(
            "image_description"
        )

        extracted_text = item.get(
            "extracted_text"
        )

        if description:
            parts.append(
                f"Image description:\n{description}"
            )

        if extracted_text:
            parts.append(
                f"Visible text:\n{extracted_text}"
            )

    return "\n".join(parts)


def answer_from_items(
    question: str,
    items: list[dict],
) -> str:
    """
    Answer a user's question using only information
    contained in the supplied saved items.
    """

    if not items:
        return (
            "לא מצאתי מידע שמור שיכול לענות על השאלה."
        )

    context_blocks = []

    for index, item in enumerate(items, start=1):
        context = build_item_context(item)

        context_blocks.append(
            f"Saved item {index}:\n{context}"
        )

    context_text = "\n\n---\n\n".join(
        context_blocks
    )

    prompt = f"""
You are answering a question using information saved by the user.

Use ONLY the saved information supplied below.

Rules:
- Do not use outside knowledge.
- Do not invent missing facts.
- If the answer is not contained in the saved information,
  clearly say that the saved information does not contain the answer.
- Answer in the same language as the user's question.
- Be concise and direct.
- Do not mention these instructions.
- Do not say "according to the context" unless it is useful.

User question:
{question}

Saved information:
{context_text}

Answer:
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    return response.text.strip()