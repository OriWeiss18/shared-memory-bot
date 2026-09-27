from app.embeddings import (
    build_item_search_text,
    generate_item_embedding,
)
from app.processors.image_processor import analyze_image_bytes


def prepare_image_item(
    image_bytes: bytes,
    mime_type: str,
) -> dict:
    """
    Analyze an image and prepare all searchable data needed
    before persisting it to the database.
    """

    metadata = analyze_image_bytes(
        image_bytes=image_bytes,
        mime_type=mime_type,
    )

    content = "\n".join(
        part
        for part in [
            metadata.get("description"),
            metadata.get("extracted_text"),
        ]
        if part
    )

    search_text = build_item_search_text(
        title=metadata.get("title"),
        category=metadata.get("category"),
        tags=metadata.get("tags", []),
        summary=metadata.get("summary"),
        content=content,
    )

    embedding = generate_item_embedding(
        text=search_text,
        title=metadata.get("title"),
    )

    return {
        **metadata,
        "search_text": search_text,
        "embedding": embedding,
    }