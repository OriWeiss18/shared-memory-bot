import json
import mimetypes
import sys
from pathlib import Path

from app.ai import enrich_text_item
from app.embeddings import (
    build_item_search_text,
    generate_item_embedding,
)
from app.ingestion import prepare_image_item
from app.mock_repository import (
    MOCK_DB_PATH,
    add_mock_item,
    copy_image_to_web,
    get_created_at,
)


def preview_text(
    text: str,
) -> tuple[dict, dict]:
    enrichment = enrich_text_item(text)

    search_text = build_item_search_text(
        title=enrichment.get("title"),
        category=enrichment.get("category"),
        tags=enrichment.get("tags", []),
        summary=enrichment.get("summary"),
        content=text,
    )

    embedding = generate_item_embedding(
        text=search_text,
        title=enrichment.get("title"),
    )

    preview = {
        "source_type": "text",
        "original_text": text,
        "title": enrichment.get("title"),
        "category": enrichment.get("category"),
        "tags": enrichment.get("tags", []),
        "summary": enrichment.get("summary"),
        "search_text": search_text,
        "embedding_dimensions": len(embedding),
    }

    mock_item = {
        "source_type": "text",
        "original_text": text,
        "title": enrichment.get("title"),
        "category": enrichment.get("category"),
        "tags": enrichment.get("tags", []),
        "summary": enrichment.get("summary"),
        "created_at": get_created_at(),
    }

    return preview, mock_item


def preview_image(
    path: str,
) -> tuple[dict, dict]:
    image_path = Path(path)

    if not image_path.is_file():
        raise FileNotFoundError(
            f"Image file not found: {image_path}"
        )

    mime_type, _ = mimetypes.guess_type(
        image_path.name
    )

    if mime_type is None:
        raise ValueError(
            "Could not determine image MIME type"
        )

    prepared = prepare_image_item(
        image_bytes=image_path.read_bytes(),
        mime_type=mime_type,
    )

    image_url = copy_image_to_web(
        image_path
    )

    preview = {
        "source_type": "image",
        "file": str(image_path),
        "mime_type": mime_type,
        "title": prepared.get("title"),
        "category": prepared.get("category"),
        "tags": prepared.get("tags", []),
        "summary": prepared.get("summary"),
        "description": prepared.get("description"),
        "extracted_text": prepared.get(
            "extracted_text"
        ),
        "search_text": prepared.get(
            "search_text"
        ),
        "embedding_dimensions": len(
            prepared.get("embedding", [])
        ),
        "image_url": image_url,
    }

    mock_item = {
        "source_type": "image",
        "mime_type": mime_type,
        "title": prepared.get("title"),
        "category": prepared.get("category"),
        "tags": prepared.get("tags", []),
        "summary": prepared.get("summary"),
        "image_description": prepared.get(
            "description"
        ),
        "extracted_text": prepared.get(
            "extracted_text"
        ),
        "image_url": image_url,
        "created_at": get_created_at(),
    }

    return preview, mock_item


def print_usage():
    print(
        "Usage:\n"
        "  python -m scripts.preview_ingestion "
        'text "your text here"\n'
        "  python -m scripts.preview_ingestion "
        'image "path\\to\\image.jpg"'
    )


def main():
    if len(sys.argv) < 3:
        print_usage()
        raise SystemExit(1)

    mode = sys.argv[1].lower()

    try:
        if mode == "text":
            text = " ".join(
                sys.argv[2:]
            )

            preview, mock_item = (
                preview_text(text)
            )

        elif mode == "image":
            preview, mock_item = (
                preview_image(
                    sys.argv[2]
                )
            )

        else:
            print_usage()
            raise SystemExit(1)

        saved_item = add_mock_item(
            mock_item
        )

    except Exception as exc:
        print("\nPreview failed:")
        print(exc)
        raise SystemExit(1)

    print("\n=== Gemini preview ===")

    print(
        json.dumps(
            preview,
            ensure_ascii=False,
            indent=2,
        )
    )

    print("\n=== Added to mock DB ===")
    print(
        f"ID: {saved_item['id']}"
    )
    print(
        f"Title: {saved_item.get('title')}"
    )
    print(
        f"Category: {saved_item.get('category')}"
    )
    print(
        "Source type: "
        f"{saved_item.get('source_type')}"
    )
    print(
        f"Mock DB: {MOCK_DB_PATH}"
    )

    if saved_item.get("image_url"):
        print(
            "Image URL: "
            f"{saved_item['image_url']}"
        )


if __name__ == "__main__":
    main()