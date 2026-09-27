import os

import httpx
from dotenv import load_dotenv


load_dotenv()

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

GRAPH_API_VERSION = "v26.0"


def send_text_message(to: str, text: str) -> dict:
    if not WHATSAPP_ACCESS_TOKEN:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is missing")

    if not WHATSAPP_PHONE_NUMBER_ID:
        raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID is missing")

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": text,
        },
    }

    response = httpx.post(
        url,
        headers=headers,
        json=payload,
        timeout=20.0,
    )

    response.raise_for_status()

    return response.json()

def get_media_url(media_id: str) -> str:
    if not WHATSAPP_ACCESS_TOKEN:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is missing")

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/"
        f"{media_id}"
    )

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    }

    response = httpx.get(
        url,
        headers=headers,
        timeout=20.0,
    )

    response.raise_for_status()

    data = response.json()

    media_url = data.get("url")

    if not media_url:
        raise RuntimeError("WhatsApp media URL is missing")

    return media_url


def download_media(media_id: str) -> bytes:
    if not WHATSAPP_ACCESS_TOKEN:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is missing")

    media_url = get_media_url(media_id)

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    }

    response = httpx.get(
        media_url,
        headers=headers,
        timeout=30.0,
    )

    response.raise_for_status()

    return response.content

def upload_image_media(
    image_bytes: bytes,
    mime_type: str,
) -> str:
    if not WHATSAPP_ACCESS_TOKEN:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is missing")

    if not WHATSAPP_PHONE_NUMBER_ID:
        raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID is missing")

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/media"
    )

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    }

    data = {
        "messaging_product": "whatsapp",
    }

    files = {
        "file": (
            "image",
            image_bytes,
            mime_type,
        )
    }

    response = httpx.post(
        url,
        headers=headers,
        data=data,
        files=files,
        timeout=30.0,
    )

    response.raise_for_status()

    result = response.json()

    media_id = result.get("id")

    if not media_id:
        raise RuntimeError("WhatsApp media ID is missing")

    return media_id


def send_image_message(
    to: str,
    image_bytes: bytes,
    mime_type: str,
    caption: str | None = None,
):
    media_id = upload_image_media(
        image_bytes=image_bytes,
        mime_type=mime_type,
    )

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    image_payload = {
        "id": media_id,
    }

    if caption:
        image_payload["caption"] = caption

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": image_payload,
    }

    response = httpx.post(
        url,
        headers=headers,
        json=payload,
        timeout=20.0,
    )

    response.raise_for_status()

    return response.json()