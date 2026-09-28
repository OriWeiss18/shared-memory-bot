from app.ai import (
    classify_intent,
    enrich_text_item,
    fallback_classify_intent,
)
from app.embeddings import (
    build_item_search_text,
    generate_item_embedding,
)
from app.mock_repository import (
    add_mock_item,
    get_created_at,
    search_mock_items,
)
from app.processors.url_processor import (
    extract_url,
    fetch_url_content,
)
from app.rag import answer_from_items
from app.search import infer_preferred_source_type


RAG_QUESTION_TERMS = [
    "כמה",
    "מתי",
    "איך",
    "למה",
    "מי",
    "איזה",
    "איזו",
    "אילו",
    "האם",
    "באיזה",
    "באיזו",
    "מה ",
    "what",
    "how",
    "when",
    "why",
    "who",
    "which",
]

DIRECT_RETURN_TERMS = [
    "תשלח",
    "תשלחי",
    "שלח לי",
    "שלחי לי",
    "תביא",
    "תביאי",
    "תראה",
    "תראי",
    "תחזיר",
    "תחזירי",
    "קישור",
    "לינק",
    "תמונה",
    "צילום",
    "send me",
    "show me",
    "give me",
]


def classify_with_fallback(
    text: str,
) -> dict:
    try:
        return classify_intent(text)

    except Exception as exc:
        print(
            "AI intent classification unavailable, "
            "using fallback:"
        )
        print(exc)

        return fallback_classify_intent(
            text
        )


def should_use_rag(
    text: str,
) -> bool:
    lowered = text.lower().strip()

    # Explicit requests to return the saved item itself
    # should not become RAG answers.
    if any(
        term in lowered
        for term in DIRECT_RETURN_TERMS
    ):
        return False

    if "?" in lowered:
        return True

    return any(
        lowered.startswith(term)
        or f" {term}" in lowered
        for term in RAG_QUESTION_TERMS
    )


def build_direct_reply(
    item: dict,
) -> str:
    source_type = item.get(
        "source_type"
    )

    if source_type == "text":
        return (
            item.get("original_text")
            or item.get("summary")
            or "מצאתי את הפריט."
        )

    if source_type == "url":
        return (
            item.get("original_url")
            or item.get("summary")
            or "מצאתי את הקישור."
        )

    if source_type == "image":
        title = (
            item.get("title")
            or "תמונה שמורה"
        )

        image_url = item.get(
            "image_url"
        )

        if image_url:
            return (
                f"{title}\n"
                f"{image_url}"
            )

        return title

    return (
        item.get("summary")
        or item.get("title")
        or "מצאתי את הפריט."
    )


def save_text_to_mock(
    text: str,
) -> dict:
    enrichment = enrich_text_item(
        text
    )

    search_text = build_item_search_text(
        title=enrichment.get("title"),
        category=enrichment.get("category"),
        tags=enrichment.get(
            "tags",
            [],
        ),
        summary=enrichment.get(
            "summary"
        ),
        content=text,
    )

    embedding = generate_item_embedding(
        text=search_text,
        title=enrichment.get("title"),
    )

    mock_item = {
        "source_type": "text",
        "original_text": text,
        "title": enrichment.get(
            "title"
        ),
        "category": enrichment.get(
            "category"
        ),
        "tags": enrichment.get(
            "tags",
            [],
        ),
        "summary": enrichment.get(
            "summary"
        ),
        "created_at": get_created_at(),
    }

    saved_item = add_mock_item(
        mock_item
    )

    return {
        "item": saved_item,
        "embedding_dimensions": len(
            embedding
        ),
    }


def save_url_to_mock(
    url: str,
) -> dict:
    page = fetch_url_content(url)

    enrichment_input = (
        f"Page title: "
        f"{page.get('title') or ''}\n\n"
        f"Page content:\n"
        f"{page['text']}"
    )

    try:
        enrichment = enrich_text_item(
            enrichment_input
        )

    except Exception as exc:
        print(
            "AI enrichment unavailable "
            "for URL, using fallback:"
        )
        print(exc)

        enrichment = {
            "title": (
                page.get("title")
                or "Saved link"
            ),
            "category": "Other",
            "tags": [],
            "summary": page[
                "text"
            ][:300],
        }

    search_text = build_item_search_text(
        title=enrichment.get("title"),
        category=enrichment.get(
            "category"
        ),
        tags=enrichment.get(
            "tags",
            [],
        ),
        summary=enrichment.get(
            "summary"
        ),
        content=page["text"],
    )

    embedding = generate_item_embedding(
        text=search_text,
        title=enrichment.get("title"),
    )

    mock_item = {
        "source_type": "url",
        "original_url": url,
        "extracted_text": page[
            "text"
        ],
        "title": enrichment.get(
            "title"
        ),
        "category": enrichment.get(
            "category"
        ),
        "tags": enrichment.get(
            "tags",
            [],
        ),
        "summary": enrichment.get(
            "summary"
        ),
        "created_at": get_created_at(),
    }

    saved_item = add_mock_item(
        mock_item
    )

    return {
        "item": saved_item,
        "embedding_dimensions": len(
            embedding
        ),
    }


def search_mock_memory(
    text: str,
    search_query: str | None,
) -> dict:
    query = (
        search_query
        or text
    )

    preferred_source_type = (
        infer_preferred_source_type(
            query
        )
    )

    use_rag = should_use_rag(
        text
    )

    matches = search_mock_items(
        query=query,
        limit=3 if use_rag else 1,
        preferred_source_type=(
            preferred_source_type
        ),
    )

    if not matches:
        return {
            "text": (
                "לא מצאתי מידע שמור "
                "שמתאים למה שחיפשת."
            ),
            "action": "SEARCH",
            "found": False,
            "rag": use_rag,
        }

    if not use_rag:
        return {
            "text": build_direct_reply(
                matches[0]
            ),
            "action": "SEARCH",
            "found": True,
            "rag": False,
            "item": matches[0],
        }

    try:
        answer = answer_from_items(
            question=text,
            items=matches,
        )

        return {
            "text": answer,
            "action": "SEARCH",
            "found": True,
            "rag": True,
            "items": matches,
        }

    except Exception as exc:
        print(
            "RAG unavailable, "
            "returning best item:"
        )
        print(exc)

        return {
            "text": build_direct_reply(
                matches[0]
            ),
            "action": "SEARCH",
            "found": True,
            "rag": False,
            "rag_failed": True,
            "item": matches[0],
        }


def process_text_message(
    text: str,
) -> dict:
    text = text.strip()

    if not text:
        return {
            "text": "ההודעה ריקה.",
            "action": "NONE",
        }

    url = extract_url(text)

    if url:
        intent_result = {
            "intent": "SAVE",
            "search_query": None,
        }

    else:
        intent_result = (
            classify_with_fallback(
                text
            )
        )

    intent = intent_result.get(
        "intent"
    )

    print(
        "Intent:",
        intent_result,
    )

    if intent == "SAVE":
        try:
            if url:
                result = save_url_to_mock(
                    url
                )

                item = result["item"]

                return {
                    "text": (
                        "נשמר ✅\n"
                        f"{item.get('title')}"
                    ),
                    "action": "SAVE",
                    "source_type": "url",
                    "item": item,
                }

            result = save_text_to_mock(
                text
            )

            item = result["item"]

            return {
                "text": (
                    "נשמר ✅\n"
                    f"{item.get('title')}"
                ),
                "action": "SAVE",
                "source_type": "text",
                "item": item,
            }

        except Exception as exc:
            print(
                "Save failed:"
            )
            print(exc)

            return {
                "text": (
                    "לא הצלחתי לשמור "
                    "את הפריט כרגע."
                ),
                "action": "SAVE",
                "saved": False,
            }

    if intent == "SEARCH":
        return search_mock_memory(
            text=text,
            search_query=intent_result.get(
                "search_query"
            ),
        )

    return {
        "text": (
            "לא הבנתי אם לשמור "
            "או לחפש את המידע."
        ),
        "action": "UNKNOWN",
    }