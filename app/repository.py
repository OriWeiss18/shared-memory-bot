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
    # 1. Check the user's currently active space
    user_response = (
        supabase.table("app_users")
        .select("active_space_id")
        .eq("id", user_id)
        .single()
        .execute()
    )

    active_space_id = user_response.data.get("active_space_id")

    if active_space_id:
        # Make sure the user is still a member of that space
        membership_response = (
            supabase.table("space_members")
            .select("space_id")
            .eq("user_id", user_id)
            .eq("space_id", active_space_id)
            .limit(1)
            .execute()
        )

        if membership_response.data:
            return active_space_id

    # 2. If there is no valid active space,
    # use one of the user's existing memberships
    membership_response = (
        supabase.table("space_members")
        .select("space_id")
        .eq("user_id", user_id)
        .order("joined_at")
        .limit(1)
        .execute()
    )

    if membership_response.data:
        space_id = membership_response.data[0]["space_id"]

        supabase.table("app_users").update({
            "active_space_id": space_id,
        }).eq("id", user_id).execute()

        return space_id

    # 3. User has no spaces yet — create the first one
    space_response = (
        supabase.table("spaces")
        .insert({
            "name": "My Shared Memory",
        })
        .execute()
    )

    space_id = space_response.data[0]["id"]

    supabase.table("space_members").insert({
        "space_id": space_id,
        "user_id": user_id,
        "role": "owner",
    }).execute()

    supabase.table("app_users").update({
        "active_space_id": space_id,
    }).eq("id", user_id).execute()

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

def build_image_item_data(
    space_id: str,
    sender_user_id: str,
    source_message_id: str,
    storage_path: str,
    mime_type: str,
    title: str | None,
    summary: str | None,
    category: str | None,
    tags: list[str],
    description: str | None,
    extracted_text: str | None,
    embedding: list[float],
):
    return {
        "space_id": space_id,
        "sender_user_id": sender_user_id,
        "source_platform": "whatsapp",
        "source_message_id": source_message_id,
        "source_type": "image",
        "storage_path": storage_path,
        "mime_type": mime_type,
        "title": title,
        "summary": summary,
        "category": category,
        "tags": tags,
        "image_description": description,
        "extracted_text": extracted_text,
        "embedding": embedding,
        "processing_status": "processed",
    }

def save_image_item(
    space_id: str,
    sender_user_id: str,
    source_message_id: str,
    storage_path: str,
    mime_type: str,
    title: str | None,
    summary: str | None,
    category: str | None,
    tags: list[str],
    description: str | None,
    extracted_text: str | None,
    embedding: list[float],
):
    item_data = build_image_item_data(
        space_id=space_id,
        sender_user_id=sender_user_id,
        source_message_id=source_message_id,
        storage_path=storage_path,
        mime_type=mime_type,
        title=title,
        summary=summary,
        category=category,
        tags=tags,
        description=description,
        extracted_text=extracted_text,
        embedding=embedding,
    )

    response = (
        supabase.table("items")
        .insert(item_data)
        .execute()
    )

    return response.data[0]

def add_user_to_space(
    user_id: str,
    space_id: str,
    role: str = "member",
):
    # Do not create a duplicate membership
    existing = (
        supabase.table("space_members")
        .select("*")
        .eq("user_id", user_id)
        .eq("space_id", space_id)
        .limit(1)
        .execute()
    )

    if existing.data:
        return existing.data[0]

    response = (
        supabase.table("space_members")
        .insert({
            "space_id": space_id,
            "user_id": user_id,
            "role": role,
        })
        .execute()
    )

    return response.data[0]


def set_active_space(
    user_id: str,
    space_id: str,
):
    # A user may only activate a space they belong to
    membership = (
        supabase.table("space_members")
        .select("space_id")
        .eq("user_id", user_id)
        .eq("space_id", space_id)
        .limit(1)
        .execute()
    )

    if not membership.data:
        raise ValueError("User is not a member of this space")

    response = (
        supabase.table("app_users")
        .update({
            "active_space_id": space_id,
        })
        .eq("id", user_id)
        .execute()
    )

    return response.data[0]


def join_space_by_code(
    user_id: str,
    invite_code: str,
):
    normalized_code = invite_code.strip().upper()

    # Find the space with this invite code
    space_response = (
        supabase.table("spaces")
        .select("id, name, invite_code")
        .eq("invite_code", normalized_code)
        .limit(1)
        .execute()
    )

    if not space_response.data:
        return None

    space = space_response.data[0]
    space_id = space["id"]

    # Add the user if they are not already a member
    add_user_to_space(
        user_id=user_id,
        space_id=space_id,
        role="member",
    )

    # Make this the user's active space
    set_active_space(
        user_id=user_id,
        space_id=space_id,
    )

    return space