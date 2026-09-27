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

def infer_preferred_source_type(query: str) -> str | None:
    lowered = query.lower()

    image_terms = [
        "תמונה",
        "תמונות",
        "צילום",
        "צילמתי",
        "תצלום",
        "image",
        "photo",
        "picture",
    ]

    url_terms = [
        "קישור",
        "לינק",
        "url",
        "link",
    ]

    if any(term in lowered for term in image_terms):
        return "image"

    if any(term in lowered for term in url_terms):
        return "url"

    return None


def find_best_match(
    space_id: str,
    query: str,
    preferred_source_type: str | None = None,
):
    results = search_items(
        space_id=space_id,
        query=query,
        limit=10,
    )

    if not results:
        return None

    if preferred_source_type:
        matching_type_results = [
            item
            for item in results
            if item.get("source_type") == preferred_source_type
        ]

        if not matching_type_results:
            return None

        best_result = matching_type_results[0]

    else:
        best_result = results[0]

    if best_result["similarity"] < MIN_SIMILARITY:
        return None

    return best_result