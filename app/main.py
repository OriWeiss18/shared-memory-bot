import os

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import PlainTextResponse, Response

from app.ai import (
    classify_intent,
    enrich_text_item,
    fallback_classify_intent,
)
from app.database import supabase
from app.embeddings import (
    build_item_search_text,
    generate_item_embedding,
)
from app.processors.url_processor import extract_url, fetch_url_content
from app.repository import (
    get_or_create_space,
    get_or_create_user,
    save_text_item,
    save_image_item,
    backfill_missing_embeddings,
    get_item_by_message_id,
    save_url_item,
    join_space_by_code,
    create_space,
    get_active_space_details,
    list_user_spaces,
    switch_space_by_code,
    list_items_for_space,
    get_item_by_id,
)
from app.rag import answer_from_items, should_use_rag
from app.retrieval import build_reply_from_item
from app.search import (
    MIN_SIMILARITY,
    find_best_match,
    infer_preferred_source_type,
    search_items,
)
from app.ingestion import prepare_image_item
from app.storage import (
    build_image_storage_path,
    download_image,
    upload_image,
)
from app.whatsapp import (
    extract_image_message,
    extract_text_message,
)
from app.whatsapp_client import (
    download_media,
    send_image_message,
    send_text_message,
)
from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


app = FastAPI()
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app.mount(
    "/static",
    StaticFiles(directory=WEB_DIR),
    name="static",
)

load_dotenv()

WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
DASHBOARD_SPACE_ID = os.getenv("DASHBOARD_SPACE_ID")


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

@app.get("/dashboard")
def dashboard():
    return FileResponse(
        WEB_DIR / "index.html"
    )


@app.get("/api/items")
def dashboard_items():
    if not DASHBOARD_SPACE_ID:
        return {
            "error": "DASHBOARD_SPACE_ID is not configured"
        }

    return list_items_for_space(
        DASHBOARD_SPACE_ID
    )


@app.get("/api/items/{item_id}/image")
def dashboard_item_image(
    item_id: str,
):
    if not DASHBOARD_SPACE_ID:
        return Response(
            status_code=500
        )

    item = get_item_by_id(
        item_id
    )

    if (
        item is None
        or item.get("space_id") != DASHBOARD_SPACE_ID
        or item.get("source_type") != "image"
        or not item.get("storage_path")
    ):
        return Response(
            status_code=404
        )

    image_bytes = download_image(
        item["storage_path"]
    )

    return Response(
        content=image_bytes,
        media_type=(
            item.get("mime_type")
            or "application/octet-stream"
        ),
    )


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

    text_message = extract_text_message(payload)
    image_message = extract_image_message(payload)

    message = image_message or text_message

    if message is None:
        return {
            "status": "ok",
            "message": "No supported message found",
        }

    existing_item = get_item_by_message_id(message["message_id"])

    if existing_item is not None:
        print(
            "Duplicate WhatsApp message ignored:",
            message["message_id"],
        )

        return {
            "status": "ok",
            "duplicate": True,
            "item_id": existing_item["id"],
        }

    # -------------------------
    # IMAGE SAVE
    # -------------------------

    if image_message is not None:
        user = get_or_create_user(
            image_message["sender"]
        )

        space_id = get_or_create_space(
            user["id"]
        )

        try:
            image_bytes = download_media(
                image_message["media_id"]
            )

            prepared = prepare_image_item(
                image_bytes=image_bytes,
                mime_type=image_message["mime_type"],
            )

            storage_path = build_image_storage_path(
                space_id=space_id,
                mime_type=image_message["mime_type"],
            )

            upload_image(
                image_bytes=image_bytes,
                storage_path=storage_path,
                mime_type=image_message["mime_type"],
            )

            saved_item = save_image_item(
                space_id=space_id,
                sender_user_id=user["id"],
                source_message_id=image_message["message_id"],
                storage_path=storage_path,
                mime_type=image_message["mime_type"],
                title=prepared["title"],
                summary=prepared["summary"],
                category=prepared["category"],
                tags=prepared["tags"],
                description=prepared["description"],
                extracted_text=prepared["extracted_text"],
                embedding=prepared["embedding"],
            )

            send_text_message(
                to=image_message["sender"],
                text=(
                    f"נשמרה תמונה ✅\n"
                    f"{prepared['title']}"
                ),
            )

            return {
                "status": "ok",
                "intent": "SAVE",
                "source_type": "image",
                "item_id": saved_item["id"],
            }

        except Exception as exc:
            print("Image processing error:")
            print(exc)

            try:
                send_text_message(
                    to=image_message["sender"],
                    text="לא הצלחתי לשמור את התמונה.",
                )
            except Exception:
                pass

            return {
                "status": "ok",
                "saved": False,
                "source_type": "image",
                "reason": "image_processing_failed",
            }

    # From here onward we are handling text messages only.
    message = text_message
    text = message["text"].strip()

    # -------------------------
    # ACTIVE SPACE
    # -------------------------

    if text.lower() == "/space":
        user = get_or_create_user(
            message["sender"]
        )

        space = get_active_space_details(
            user["id"]
        )

        notification_sent = True

        try:
            send_text_message(
                to=message["sender"],
                text=(
                    f"המרחב הפעיל שלך:\n"
                    f"{space['name']} ✅"
                ),
            )

        except Exception as send_error:
            notification_sent = False

            print(
                "Could not send active-space response:"
            )
            print(send_error)

        return {
            "status": "ok",
            "action": "show_active_space",
            "space_id": space["id"],
            "space_name": space["name"],
            "notification_sent": notification_sent,
        }

    # -------------------------
    # SPACE INVITE CODE
    # -------------------------

    if text.lower() == "/invite":
        user = get_or_create_user(
            message["sender"]
        )

        space = get_active_space_details(
            user["id"]
        )

        notification_sent = True

        try:
            send_text_message(
                to=message["sender"],
                text=(
                    f"קוד ההזמנה למרחב "
                    f"{space['name']}:\n"
                    f"{space['invite_code']}"
                ),
            )

        except Exception as send_error:
            notification_sent = False

            print(
                "Could not send invite-code response:"
            )
            print(send_error)

        return {
            "status": "ok",
            "action": "show_invite_code",
            "space_id": space["id"],
            "space_name": space["name"],
            "invite_code": space["invite_code"],
            "notification_sent": notification_sent,
        }

    # -------------------------
    # LIST USER SPACES
    # -------------------------

    if text.lower() == "/spaces":
        user = get_or_create_user(
            message["sender"]
        )

        spaces = list_user_spaces(
            user["id"]
        )

        lines = ["המרחבים שלך:"]

        for space in spaces:
            marker = " ✅" if space["is_active"] else ""

            lines.append(
                f"• {space['name']}{marker}"
                f" ({space['role']})"
            )

        notification_sent = True

        try:
            send_text_message(
                to=message["sender"],
                text="\n".join(lines),
            )

        except Exception as send_error:
            notification_sent = False

            print(
                "Could not send spaces response:"
            )
            print(send_error)

        return {
            "status": "ok",
            "action": "list_spaces",
            "spaces": spaces,
            "notification_sent": notification_sent,
        }

    # -------------------------
    # SWITCH ACTIVE SPACE
    # -------------------------

    if text.lower() == "/switch":
        notification_sent = True

        try:
            send_text_message(
                to=message["sender"],
                text=(
                    "כדי לעבור למרחב אחר, כתבי:\n"
                    "/switch קוד_הזמנה"
                ),
            )

        except Exception as send_error:
            notification_sent = False

            print(
                "Could not send switch usage response:"
            )
            print(send_error)

        return {
            "status": "ok",
            "action": "switch_space",
            "switched": False,
            "reason": "missing_code",
            "notification_sent": notification_sent,
        }

    if text.lower().startswith("/switch "):
        invite_code = text.split(
            maxsplit=1
        )[1].strip()

        user = get_or_create_user(
            message["sender"]
        )

        result = switch_space_by_code(
            user_id=user["id"],
            invite_code=invite_code,
        )

        notification_sent = True

        if result["status"] == "not_found":
            response_text = "קוד המרחב לא נמצא."

        elif result["status"] == "not_member":
            response_text = (
                "את עדיין לא חברה במרחב הזה.\n"
                "השתמשי ב-/join כדי להצטרף."
            )

        else:
            space = result["space"]

            response_text = (
                f"המרחב הפעיל הוחלף ✅\n"
                f"{space['name']}"
            )

        try:
            send_text_message(
                to=message["sender"],
                text=response_text,
            )

        except Exception as send_error:
            notification_sent = False

            print(
                "Could not send switch-space response:"
            )
            print(send_error)

        return {
            "status": "ok",
            "action": "switch_space",
            "switched": result["status"] == "ok",
            "result": result["status"],
            "space_id": (
                result.get("space", {}).get("id")
            ),
            "notification_sent": notification_sent,
        }

    # -------------------------
    # CREATE SHARED SPACE
    # -------------------------

    if text.lower() == "/create":
        send_text_message(
            to=message["sender"],
            text=(
                "כדי ליצור מרחב חדש, כתבי:\n"
                "/create שם המרחב"
            ),
        )

        return {
            "status": "ok",
            "action": "create_space",
            "created": False,
            "reason": "missing_name",
        }

    if text.lower().startswith("/create "):
        space_name = text.split(
            maxsplit=1
        )[1].strip()

        user = get_or_create_user(
            message["sender"]
        )

        space = create_space(
            user_id=user["id"],
            name=space_name,
        )

        notification_sent = True

        try:
            send_text_message(
                to=message["sender"],
                text=(
                    f"נוצר מרחב חדש ✅\n"
                    f"{space['name']}\n\n"
                    f"קוד הזמנה: {space['invite_code']}\n"
                    f"המרחב הוגדר כפעיל."
                ),
            )

        except Exception as send_error:
            notification_sent = False

            print(
                "Could not send create-space confirmation:"
            )
            print(send_error)

        return {
            "status": "ok",
            "action": "create_space",
            "created": True,
            "space_id": space["id"],
            "invite_code": space["invite_code"],
            "notification_sent": notification_sent,
        }

    # -------------------------
    # JOIN SHARED SPACE
    # -------------------------

    if text.lower().startswith("/join "):
        invite_code = text.split(
            maxsplit=1
        )[1].strip()

        user = get_or_create_user(
            message["sender"]
        )

        space = join_space_by_code(
            user_id=user["id"],
            invite_code=invite_code,
        )

        if space is None:
            send_text_message(
                to=message["sender"],
                text="קוד ההזמנה לא נמצא.",
            )

            return {
                "status": "ok",
                "action": "join_space",
                "joined": False,
            }

        notification_sent = True

        try:
            send_text_message(
                to=message["sender"],
                text=(
                    f"הצטרפת למרחב המשותף ✅\n"
                    f"{space['name']}"
                ),
            )

        except Exception as send_error:
            notification_sent = False

            print(
                "Could not send join confirmation:"
            )
            print(send_error)

        return {
            "status": "ok",
            "action": "join_space",
            "joined": True,
            "space_id": space["id"],
            "notification_sent": notification_sent,
        }

    # -------------------------
    # INTENT
    # -------------------------

    url = extract_url(message["text"])

    if url:
        intent_result = {
            "intent": "SAVE",
            "search_query": None,
        }

    else:
        try:
            intent_result = classify_intent(
                message["text"]
            )

        except Exception as exc:
            print(
                "AI intent classification unavailable, "
                "using fallback:"
            )
            print(exc)

            intent_result = fallback_classify_intent(
                message["text"]
            )

    intent = intent_result["intent"]

    print("Intent:")
    print(intent_result)

    # -------------------------
    # SAVE
    # -------------------------

    if intent == "SAVE":
        user = get_or_create_user(
            message["sender"]
        )

        space_id = get_or_create_space(
            user["id"]
        )

        # -------------------------
        # URL SAVE
        # -------------------------

        if url:
            print("Detected URL:", url)

            try:
                page = fetch_url_content(url)

            except Exception as exc:
                print("URL fetch error:")
                print(exc)

                send_text_message(
                    to=message["sender"],
                    text=(
                        "לא הצלחתי לקרוא את "
                        "הקישור הזה."
                    ),
                )

                return {
                    "status": "ok",
                    "saved": False,
                    "reason": "url_fetch_failed",
                }

            enrichment_input = (
                f"Page title: "
                f"{page.get('title') or ''}\n\n"
                f"Page content:\n"
                f"{page['text']}"
            )

            try:
                enrichment = enrich_text_item(
                    enrichment_input
                )

            except Exception as exc:
                print(
                    "AI enrichment unavailable "
                    "for URL, using fallback:"
                )
                print(exc)

                enrichment = {
                    "title": (
                        page.get("title")
                        or "Saved link"
                    ),
                    "category": "Other",
                    "tags": [],
                    "summary": page["text"][:300],
                }

            print("AI enrichment:")
            print(enrichment)

            search_text = build_item_search_text(
                title=enrichment["title"],
                category=enrichment["category"],
                tags=enrichment["tags"],
                summary=enrichment["summary"],
                content=page["text"],
            )

            embedding = generate_item_embedding(
                search_text
            )

            saved_item = save_url_item(
                space_id=space_id,
                sender_user_id=user["id"],
                source_message_id=message["message_id"],
                original_url=url,
                extracted_text=page["text"],
                title=enrichment["title"],
                summary=enrichment["summary"],
                category=enrichment["category"],
                tags=enrichment["tags"],
                embedding=embedding,
            )

            print(
                "Saved URL item:",
                saved_item["id"],
                saved_item.get("title"),
            )

            send_text_message(
                to=message["sender"],
                text=(
                    f"נשמר ✅\n"
                    f"{enrichment.get('title', 'קישור חדש')}"
                ),
            )

            return {
                "status": "ok",
                "intent": "SAVE",
                "source_type": "url",
                "item_id": saved_item["id"],
            }

        # -------------------------
        # NORMAL TEXT SAVE
        # -------------------------

        try:
            enrichment = enrich_text_item(
                message["text"]
            )

        except Exception as exc:
            print(
                "AI error while enriching item:"
            )
            print(exc)

            send_text_message(
                to=message["sender"],
                text=(
                    "יש כרגע עומס זמני בשירות ה-AI. "
                    "נסי שוב בעוד דקה."
                ),
            )

            return {
                "status": "ok",
                "message": (
                    "AI temporarily unavailable"
                ),
            }

        print("AI enrichment:")
        print(enrichment)

        search_text = build_item_search_text(
            title=enrichment["title"],
            category=enrichment["category"],
            tags=enrichment["tags"],
            summary=enrichment["summary"],
            content=message["text"],
        )

        embedding = generate_item_embedding(
            search_text
        )

        saved_item = save_text_item(
            space_id=space_id,
            sender_user_id=user["id"],
            source_message_id=message["message_id"],
            original_text=message["text"],
            title=enrichment["title"],
            summary=enrichment["summary"],
            category=enrichment["category"],
            tags=enrichment["tags"],
            embedding=embedding,
        )

        print(
            "Saved item:",
            saved_item["id"],
            saved_item.get("title"),
        )

        send_text_message(
            to=message["sender"],
            text=(
                f"נשמר ✅\n"
                f"{enrichment.get('title', 'פריט חדש')}"
            ),
        )

        return {
            "status": "ok",
            "intent": "SAVE",
            "source_type": "text",
            "item_id": saved_item["id"],
        }

    # -------------------------
    # SEARCH
    # -------------------------

    if intent == "SEARCH":
        user = get_or_create_user(
            message["sender"]
        )

        space_id = get_or_create_space(
            user["id"]
        )

        search_query = intent_result[
            "search_query"
        ]

        preferred_source_type = (
            infer_preferred_source_type(
                search_query
            )
        )

        print("Preferred source type:")
        print(preferred_source_type)

        use_rag = should_use_rag(text)

        print("Use RAG:")
        print(use_rag)

        # -------------------------
        # RAG QUESTION
        # -------------------------

        if use_rag:
            matches = search_items(
                space_id=space_id,
                query=search_query,
                limit=5,
            )

            if preferred_source_type:
                matches = [
                    item
                    for item in matches
                    if item.get("source_type")
                    == preferred_source_type
                ]

            matches = [
                item
                for item in matches
                if item.get("similarity", 0)
                >= MIN_SIMILARITY
            ][:3]

            print("RAG matches:")
            print(matches)

            if not matches:
                send_text_message(
                    to=message["sender"],
                    text=(
                        "לא מצאתי מידע שמור "
                        "שמתאים למה ששאלת."
                    ),
                )

                return {
                    "status": "ok",
                    "intent": "SEARCH",
                    "search_query": search_query,
                    "found": False,
                    "rag": True,
                }

            try:
                answer = answer_from_items(
                    question=text,
                    items=matches,
                )

                send_text_message(
                    to=message["sender"],
                    text=answer,
                )

                print("RAG answer:")
                print(answer)

                return {
                    "status": "ok",
                    "intent": "SEARCH",
                    "search_query": search_query,
                    "found": True,
                    "rag": True,
                    "answer": answer,
                }

            except Exception as exc:
                print(
                    "RAG unavailable, "
                    "returning best item:"
                )
                print(exc)

                best_match = matches[0]

        # -------------------------
        # DIRECT SEARCH
        # -------------------------

        else:
            best_match = find_best_match(
                space_id=space_id,
                query=search_query,
                preferred_source_type=(
                    preferred_source_type
                ),
            )

        print("Search query:")
        print(search_query)

        print("Best match:")
        print(best_match)

        if best_match is None:
            send_text_message(
                to=message["sender"],
                text=(
                    "לא מצאתי פריט מספיק מתאים "
                    "למה שחיפשת."
                ),
            )

            return {
                "status": "ok",
                "intent": "SEARCH",
                "search_query": search_query,
                "found": False,
            }

        reply = build_reply_from_item(
            best_match
        )

        print("Reply:")
        print(reply)

        if (
            reply["type"] == "text"
            and reply["content"]
        ):
            whatsapp_response = (
                send_text_message(
                    to=message["sender"],
                    text=reply["content"],
                )
            )

            print("WhatsApp response:")
            print(whatsapp_response)

        elif reply["type"] == "image":
            storage_path = reply.get(
                "storage_path"
            )

            mime_type = reply.get(
                "mime_type"
            )

            if not storage_path or not mime_type:
                raise RuntimeError(
                    "Image search result is missing "
                    "storage information"
                )

            image_bytes = download_image(
                storage_path
            )

            whatsapp_response = (
                send_image_message(
                    to=message["sender"],
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    caption=reply.get("caption"),
                )
            )

            print(
                "WhatsApp image response:"
            )
            print(whatsapp_response)

        return {
            "status": "ok",
            "intent": "SEARCH",
            "search_query": search_query,
            "found": True,
            "rag": False,
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