import os

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import PlainTextResponse

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
    get_item_by_message_id,
)
from app.retrieval import build_reply_from_item
from app.search import find_best_match
from app.whatsapp import extract_text_message
from app.whatsapp_client import send_text_message


app = FastAPI()

load_dotenv()

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")


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


@app.get("/webhook")
def verify_whatsapp_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    if mode == "subscribe" and verify_token == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(content=challenge or "")

    return PlainTextResponse(
        content="Verification failed",
        status_code=403,
    )


@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    payload = await request.json()

    message = extract_text_message(payload)

    if message is None:
        return {
            "status": "ok",
            "message": "No text message found",
        }

    existing_item = get_item_by_message_id(message["message_id"])

    if existing_item is not None:
        print("Duplicate WhatsApp message ignored:", message["message_id"])

        return {
            "status": "ok",
            "duplicate": True,
            "item_id": existing_item["id"],
        }

    # Ask Gemini what the user wants to do
    try:
        intent_result = classify_intent(message["text"])
    except Exception as exc:
        print("AI error while classifying message:")
        print(exc)

        try:
            send_text_message(
                to=message["sender"],
                text="יש כרגע עומס זמני בשירות ה-AI. נסי שוב בעוד דקה.",
            )
        except Exception as send_error:
            print("Could not send temporary error message:")
            print(send_error)

        return {
            "status": "ok",
            "message": "AI temporarily unavailable",
        }

    intent = intent_result["intent"]

    print("Intent:")
    print(intent_result)

    # -------------------------
    # SAVE
    # -------------------------

    if intent == "SAVE":
        try:
            enrichment = enrich_text_item(message["text"])
        except Exception as exc:
            print("AI error while enriching item:")
            print(exc)

            send_text_message(
                to=message["sender"],
                text="יש כרגע עומס זמני בשירות ה-AI. נסי שוב בעוד דקה.",
            )

            return {
                "status": "ok",
                "message": "AI temporarily unavailable",
            }

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

        print(
            "Saved item:",
            saved_item["id"],
            saved_item.get("title"),
        )

        send_text_message(
            to=message["sender"],
            text=f"נשמר ✅\n{enrichment.get('title', 'פריט חדש')}",
        )

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
            send_text_message(
                to=message["sender"],
                text="לא מצאתי פריט מספיק מתאים למה שחיפשת.",
            )

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

        if reply["type"] == "text" and reply["content"]:
            whatsapp_response = send_text_message(
                to=message["sender"],
                text=reply["content"],
            )

            print("WhatsApp response:")
            print(whatsapp_response)

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