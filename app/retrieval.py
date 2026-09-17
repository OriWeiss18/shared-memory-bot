def build_reply_from_item(item: dict) -> dict:
    source_type = item.get("source_type")

    if source_type == "text":
        return {
            "type": "text",
            "content": item.get("original_text"),
        }

    return {
        "type": "unsupported",
        "content": None,
    }