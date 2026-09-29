import json
import mimetypes
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app.database import supabase
from app.embeddings import (
    build_item_search_text,
    generate_item_embedding,
)
from app.storage import (
    build_image_storage_path,
    upload_image,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
MOCK_FILE = ROOT_DIR / "web" / "mock_items.json"
WEB_DIR = ROOT_DIR / "web"

# Already represented by real items in Supabase:
# 10 = L'Oréal shampoo
# 22 = duplicate shakshuka
SKIP_MOCK_IDS = {"10", "22"}


def get_sender_user_id(space_id: str) -> str:
    response = (
        supabase.table("space_members")
        .select("user_id")
        .eq("space_id", space_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            f"No members found for space {space_id}"
        )

    return response.data[0]["user_id"]


def already_imported(mock_id: str) -> bool:
    response = (
        supabase.table("items")
        .select("id")
        .eq("source_platform", "mock_import")
        .eq("source_message_id", f"mock-{mock_id}")
        .limit(1)
        .execute()
    )

    return bool(response.data)


def build_embedding(item: dict) -> list[float]:
    source_type = item.get("source_type")

    if source_type == "text":
        content = item.get("original_text") or ""

    elif source_type == "url":
        content = (
            item.get("extracted_text")
            or item.get("original_url")
            or ""
        )

    elif source_type == "image":
        content = " ".join(
            part
            for part in [
                item.get("image_description"),
                item.get("extracted_text"),
            ]
            if part
        )

    else:
        content = ""

    search_text = build_item_search_text(
        title=item.get("title"),
        category=item.get("category"),
        tags=item.get("tags") or [],
        summary=item.get("summary"),
        content=content,
    )

    return generate_item_embedding(search_text)


def prepare_image_fields(
    item: dict,
    space_id: str,
) -> dict:
    image_url = item.get("image_url")

    if not image_url:
        raise RuntimeError(
            f"Image item {item['id']} has no image_url"
        )

    relative_path = image_url.removeprefix("/static/")
    local_path = WEB_DIR / relative_path

    if not local_path.exists():
        raise RuntimeError(
            f"Image file not found: {local_path}"
        )

    mime_type, _ = mimetypes.guess_type(local_path.name)

    if mime_type not in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        raise RuntimeError(
            f"Unsupported image type: {mime_type}"
        )

    image_bytes = local_path.read_bytes()

    storage_path = build_image_storage_path(
        space_id=space_id,
        mime_type=mime_type,
    )

    upload_image(
        image_bytes=image_bytes,
        storage_path=storage_path,
        mime_type=mime_type,
    )

    return {
        "storage_path": storage_path,
        "mime_type": mime_type,
        "image_description": item.get(
            "image_description"
        ),
        "extracted_text": item.get(
            "extracted_text"
        ),
    }


def import_item(
    item: dict,
    space_id: str,
    sender_user_id: str,
):
    mock_id = str(item["id"])

    if mock_id in SKIP_MOCK_IDS:
        print(
            f"SKIP {mock_id}: {item.get('title')}"
        )
        return

    if already_imported(mock_id):
        print(
            f"ALREADY IMPORTED {mock_id}: "
            f"{item.get('title')}"
        )
        return

    embedding = build_embedding(item)

    payload = {
        "space_id": space_id,
        "sender_user_id": sender_user_id,
        "source_platform": "mock_import",
        "source_message_id": f"mock-{mock_id}",
        "source_type": item["source_type"],
        "original_text": item.get("original_text"),
        "original_url": item.get("original_url"),
        "title": item.get("title"),
        "summary": item.get("summary"),
        "category": item.get("category"),
        "tags": item.get("tags") or [],
        "embedding": embedding,
        "processing_status": "processed",
        "created_at": item.get("created_at"),
        "metadata": {
            "import_source": "web/mock_items.json",
            "mock_id": mock_id,
        },
    }

    if item["source_type"] == "url":
        payload["extracted_text"] = item.get(
            "extracted_text"
        )

    if item["source_type"] == "image":
        payload.update(
            prepare_image_fields(
                item=item,
                space_id=space_id,
            )
        )

    response = (
        supabase.table("items")
        .insert(payload)
        .execute()
    )

    saved = response.data[0]

    print(
        f"IMPORTED {mock_id}: "
        f"{saved.get('title')}"
    )


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python scripts/import_mock_items.py "
            "<space_id>"
        )

    space_id = sys.argv[1]

    sender_user_id = get_sender_user_id(
        space_id
    )

    items = json.loads(
        MOCK_FILE.read_text(
            encoding="utf-8"
        )
    )

    print(f"Found {len(items)} mock items")
    print(f"Importing into space: {space_id}")
    print()

    for item in items:
        import_item(
            item=item,
            space_id=space_id,
            sender_user_id=sender_user_id,
        )

    print()
    print("Import complete.")


if __name__ == "__main__":
    main()
