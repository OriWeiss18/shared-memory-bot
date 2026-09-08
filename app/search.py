from app.database import supabase
from app.embeddings import generate_query_embedding


MIN_SIMILARITY = 0.62


def search_items(
    space_id: str,
    query: str,
    limit: int = 5,
):
    query_embedding = generate_query_embedding(query)

    response = (
        supabase.rpc(
            "match_items",
            {
                "query_embedding": query_embedding,
                "query_space_id": space_id,
                "match_count": limit,
            },
        )
        .execute()
    )

    return response.data


def find_best_match(
    space_id: str,
    query: str,
):
    results = search_items(
        space_id=space_id,
        query=query,
    )

    if not results:
        return None

    best_result = results[0]

    if best_result["similarity"] < MIN_SIMILARITY:
        return None

    return best_result