import os
from uuid import uuid4

from app.database import supabase


IMAGE_BUCKET = os.getenv(
    "SUPABASE_IMAGE_BUCKET",
    "item-images",
)


def build_image_storage_path(
    space_id: str,
    mime_type: str,
) -> str:
    extension_by_mime = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }

    extension = extension_by_mime.get(mime_type)

    if extension is None:
        raise ValueError(
            f"Unsupported image type: {mime_type}"
        )

    return f"{space_id}/{uuid4()}.{extension}"


def upload_image(
    image_bytes: bytes,
    storage_path: str,
    mime_type: str,
) -> str:
    supabase.storage.from_(IMAGE_BUCKET).upload(
        path=storage_path,
        file=image_bytes,
        file_options={
            "content-type": mime_type,
            "upsert": "false",
        },
    )

    return storage_path


def download_image(
    storage_path: str,
) -> bytes:
    return supabase.storage.from_(IMAGE_BUCKET).download(
        storage_path
    )