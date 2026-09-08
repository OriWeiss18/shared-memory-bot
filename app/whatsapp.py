def extract_text_message(payload: dict):
    """
    Extract a text message from a WhatsApp webhook payload.
    Returns None if the payload does not contain a text message.
    """

    try:
        value = payload["entry"][0]["changes"][0]["value"]

        messages = value.get("messages", [])

        if not messages:
            return None

        message = messages[0]

        if message.get("type") != "text":
            return None

        return {
            "sender": message.get("from"),
            "message_id": message.get("id"),
            "text": message.get("text", {}).get("body", ""),
        }

    except (KeyError, IndexError, TypeError):
        return None