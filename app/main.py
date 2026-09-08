from fastapi import FastAPI, Request

from app.database import supabase
from app.whatsapp import extract_text_message
from app.repository import (
    save_text_item,
    get_or_create_user,
    get_or_create_space,
)
from app.ai import classify_intent, enrich_text_item
from app.search import search_items

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

        saved_item = save_text_item(
            sender=message["sender"],
            message_id=message["message_id"],
            text=message["text"],
            enrichment=enrichment,
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

        results = search_items(
            space_id=space_id,
            query=search_query,
        )

        print("Search query:")
        print(search_query)

        print("Search results:")
        print(results)

        return {
            "status": "ok",
            "intent": "SEARCH",
            "search_query": search_query,
            "results": results,
        }

    return {
        "status": "error",
        "message": "Unknown intent",
    }