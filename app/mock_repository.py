import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4


PROJECT_DIR = Path(__file__).resolve().parent.parent

MOCK_DB_PATH = (
    PROJECT_DIR
    / "web"
    / "mock_items.json"
)

WEB_IMAGES_DIR = (
    PROJECT_DIR
    / "web"
    / "images"
)


def load_mock_items() -> list[dict]:
    if not MOCK_DB_PATH.exists():
        return []

    with MOCK_DB_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_mock_items(
    items: list[dict],
) -> None:
    MOCK_DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with MOCK_DB_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            items,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")


def get_next_mock_id(
    items: list[dict],
) -> str:
    numeric_ids = []

    for item in items:
        try:
            numeric_ids.append(
                int(item.get("id"))
            )

        except (TypeError, ValueError):
            continue

    if not numeric_ids:
        return "1"

    return str(
        max(numeric_ids) + 1
    )


def get_created_at() -> str:
    return (
        datetime.now()
        .astimezone()
        .isoformat(timespec="seconds")
    )


def add_mock_item(
    item: dict,
) -> dict:
    items = load_mock_items()

    saved_item = {
        "id": get_next_mock_id(items),
        **item,
    }

    items.append(saved_item)

    save_mock_items(items)

    return saved_item


def copy_image_to_web(
    image_path: Path,
) -> str:
    WEB_IMAGES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    suffix = image_path.suffix.lower()

    unique_name = (
        f"{image_path.stem}_"
        f"{uuid4().hex[:8]}"
        f"{suffix}"
    )

    destination = (
        WEB_IMAGES_DIR
        / unique_name
    )

    shutil.copy2(
        image_path,
        destination,
    )

    return (
        f"/static/images/"
        f"{unique_name}"
    )


def _tokenize(
    text: str,
) -> list[str]:
    words = re.findall(
        r"[\w\u0590-\u05FF]+",
        text.lower(),
    )

    stop_words = {
        "לי",
        "את",
        "של",
        "על",
        "עם",
        "זה",
        "זו",
        "הזה",
        "הזאת",
        "אני",
        "רוצה",
        "תביא",
        "תביאי",
        "תשלח",
        "תשלחי",
        "שלח",
        "שלחי",
        "תראה",
        "תראי",
        "מצא",
        "תמצא",
        "תמצאי",
        "the",
        "a",
        "an",
        "of",
        "to",
        "and",
        "me",
        "show",
        "send",
        "find",
    }

    return [
        word
        for word in words
        if len(word) > 1
        and word not in stop_words
    ]


def _item_search_text(
    item: dict,
) -> str:
    parts = [
        item.get("title"),
        item.get("summary"),
        item.get("category"),
        " ".join(
            item.get("tags") or []
        ),
        item.get("original_text"),
        item.get("original_url"),
        item.get("extracted_text"),
        item.get("image_description"),
    ]

    return " ".join(
        str(part)
        for part in parts
        if part
    ).lower()


def search_mock_items(
    query: str,
    limit: int = 5,
    preferred_source_type: str | None = None,
) -> list[dict]:
    items = load_mock_items()

    if preferred_source_type:
        items = [
            item
            for item in items
            if item.get("source_type")
            == preferred_source_type
        ]

    query_words = _tokenize(query)

    if not query_words:
        return []

    scored_items = []

    for item in items:
        title = (
            item.get("title")
            or ""
        ).lower()

        tags = " ".join(
            item.get("tags")
            or []
        ).lower()

        searchable_text = (
            _item_search_text(item)
        )

        score = 0

        for word in query_words:
            if word in title:
                score += 4

            if word in tags:
                score += 3

            if word in searchable_text:
                score += 1

        if score > 0:
            scored_items.append(
                (
                    score,
                    item.get(
                        "created_at",
                        "",
                    ),
                    item,
                )
            )

    scored_items.sort(
        key=lambda result: (
            result[0],
            result[1],
        ),
        reverse=True,
    )

    return [
        item
        for _, _, item
        in scored_items[:limit]
    ]