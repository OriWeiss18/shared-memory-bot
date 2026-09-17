from app.database import supabase
from app.embeddings import build_item_search_text, generate_item_embedding

def get_or_create_user(whatsapp_number: str):
    # Try to find an existing user
    response = (
        supabase.table("app_users")
        .select("*")
        .eq("whatsapp_number", whatsapp_number)
        .execute()
    )

    if response.data:
        return response.data[0]

    # Otherwise create one
    response = (
        supabase.table("app_users")
        .insert({
            "whatsapp_number": whatsapp_number,
        })
        .execute()
    )

    return response.data[0]


def get_or_create_space(user_id: str):
    # Check whether this user already belongs to a space
    response = (
        supabase.table("space_members")
        .select("space_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]["space_id"]

    # For now, automatically create a first space
    space_response = (
        supabase.table("spaces")
        .insert({
            "name": "My Shared Memory"
        })
        .execute()
    )

    space_id = space_response.data[0]["id"]

    supabase.table("space_members").insert({
        "space_id": space_id,
        "user_id": user_id,
        "role": "owner",
    }).execute()

    return space_id


def get_item_by_message_id(message_id: str):
    response = (
        supabase.table("items")
        .select("*")
        .eq("source_platform", "whatsapp")
        .eq("source_message_id", message_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def save_text_item(
    space_id: str,
    sender_user_id: str,
    source_message_id: str,
    original_text: str,
    title: str | None,
    summary: str | None,
    category: str | None,
    tags: list[str],
    embedding: list[float],
):
    item_data = {
        "space_id": space_id,
        "sender_user_id": sender_user_id,
        "source_platform": "whatsapp",
        "source_message_id": source_message_id,
        "source_type": "text",
        "original_text": original_text,
        "title": title,
        "summary": summary,
        "category": category,
        "tags": tags,
        "embedding": embedding,
        "processing_status": "processed",
    }

    response = (
        supabase.table("items")
        .insert(item_data)
        .execute()
    )

    return response.data[0]

def backfill_missing_embeddings():
    response = (
        supabase.table("items")
        .select("*")
        .is_("embedding", "null")
        .execute()
    )

    items = response.data

    updated = []

    for item in items:
        search_text = build_item_search_text(
            original_text=item.get("original_text"),
            title=item.get("title"),
            summary=item.get("summary"),
            category=item.get("category"),
            tags=item.get("tags", []),
        )

        embedding = generate_item_embedding(
            text=search_text,
            title=item.get("title"),
        )

        (
            supabase.table("items")
            .update({
                "embedding": embedding
            })
            .eq("id", item["id"])
            .execute()
        )

        updated.append(item["id"])

    return updated


def save_url_item(
    space_id: str,
    sender_user_id: str,
    source_message_id: str,
    original_url: str,
    extracted_text: str,
    title: str | None,
    summary: str | None,
    category: str | None,
    tags: list[str],
    embedding: list[float],
):
    item_data = {
        "space_id": space_id,
        "sender_user_id": sender_user_id,
        "source_platform": "whatsapp",
        "source_message_id": source_message_id,
        "source_type": "url",
        "original_url": original_url,
        "extracted_text": extracted_text,
        "title": title,
        "summary": summary,
        "category": category,
        "tags": tags,
        "embedding": embedding,
        "processing_status": "processed",
    }

    response = (
        supabase.table("items")
        .insert(item_data)
        .execute()
    )

    return response.data[0]