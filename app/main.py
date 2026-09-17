from fastapi import FastAPI, Request

from app.ai import classify_intent, enrich_text_item
from app.database import supabase
from app.embeddings import (
    build_item_search_text,
    generate_item_embedding,
)
from app.repository import (
    get_or_create_space,
    get_or_create_user,
    save_text_item,
    backfill_missing_embeddings,
)
from app.retrieval import build_reply_from_item
from app.search import find_best_match
from app.whatsapp import extract_text_message


app = FastAPI()


@app.get("/")
def root():
    return {
        "message": "Shared Memory Bot is running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/db-test")
def db_test():
    response = (
        supabase.table("items")
        .select("id")
        .limit(1)
        .execute()
    )

    return {
        "status": "ok",
        "database": "connected",
        "items_found": len(response.data),
    }


@app.get("/intent-test")
def intent_test(text: str):
    return classify_intent(text)


@app.get("/embedding-test")
def embedding_test():
    embedding = generate_item_embedding(
        text="מתכון לשקשוקה עם עגבניות וביצים",
        title="מתכון לשקשוקה",
    )

    return {
        "status": "ok",
        "dimensions": len(embedding),
        "first_values": embedding[:5],
    }


@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    payload = await request.json()

    message = extract_text_message(payload)

    if message is None:
        return {
            "status": "ok",
            "message": "No text message found",
        }

    # Ask Gemini what the user wants to do
    intent_result = classify_intent(message["text"])
    intent = intent_result["intent"]

    print("Intent:")
    print(intent_result)

    # -------------------------
    # SAVE
    # -------------------------

    if intent == "SAVE":
        enrichment = enrich_text_item(message["text"])

        print("AI enrichment:")
        print(enrichment)

        search_text = build_item_search_text(
            original_text=message["text"],
            title=enrichment.get("title"),
            summary=enrichment.get("summary"),
            category=enrichment.get("category"),
            tags=enrichment.get("tags", []),
        )

        embedding = generate_item_embedding(
            text=search_text,
            title=enrichment.get("title"),
        )

        saved_item = save_text_item(
            sender=message["sender"],
            message_id=message["message_id"],
            text=message["text"],
            enrichment=enrichment,
            embedding=embedding,
        )

        print("Saved item:")
        print(saved_item)

        return {
            "status": "ok",
            "intent": "SAVE",
            "message": "Saved",
            "item_id": saved_item["id"],
            "enrichment": enrichment,
        }

    # -------------------------
    # SEARCH
    # -------------------------

    if intent == "SEARCH":
        user = get_or_create_user(message["sender"])
        space_id = get_or_create_space(user["id"])

        search_query = intent_result["search_query"]

        best_match = find_best_match(
            space_id=space_id,
            query=search_query,
        )

        print("Search query:")
        print(search_query)

        print("Best match:")
        print(best_match)

        if best_match is None:
            return {
                "status": "ok",
                "intent": "SEARCH",
                "search_query": search_query,
                "found": False,
                "message": "No relevant item found",
            }

        reply = build_reply_from_item(best_match)

        print("Reply:")
        print(reply)

        return {
            "status": "ok",
            "intent": "SEARCH",
            "search_query": search_query,
            "found": True,
            "result": best_match,
            "reply": reply,
        }

    return {
        "status": "error",
        "message": "Unsupported intent",
    }


@app.post("/backfill-embeddings")
def backfill_embeddings():
    updated = backfill_missing_embeddings()

    return {
        "status": "ok",
        "updated_count": len(updated),
        "updated_items": updated,
    }