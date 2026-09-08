from app.database import supabase


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


def save_text_item(
    sender: str,
    message_id: str,
    text: str,
    enrichment: dict | None = None,
):
    user = get_or_create_user(sender)
    space_id = get_or_create_space(user["id"])

    item_data = {
        "space_id": space_id,
        "sender_user_id": user["id"],
        "source_platform": "whatsapp",
        "source_message_id": message_id,
        "source_type": "text",
        "original_text": text,
        "processing_status": "pending",
    }

    if enrichment:
        item_data.update({
            "title": enrichment.get("title"),
            "summary": enrichment.get("summary"),
            "category": enrichment.get("category"),
            "tags": enrichment.get("tags", []),
            "processing_status": "processed",
        })

    response = (
        supabase.table("items")
        .insert(item_data)
        .execute()
    )

    return response.data[0]