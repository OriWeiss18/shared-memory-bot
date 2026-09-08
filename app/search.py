from app.database import supabase


def search_items(space_id: str, query: str, limit: int = 5):
    response = (
        supabase.table("items")
        .select("*")
        .eq("space_id", space_id)
        .ilike("original_text", f"%{query}%")
        .limit(limit)
        .execute()
    )

    return response.data