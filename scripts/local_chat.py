from app.message_service import process_text_message


def main():
    print("\nShared Memory - Local Chat")
    print("==========================")
    print("Type /quit to exit.")

    while True:
        try:
            message = input("\nYou: ").strip()

        except (EOFError, KeyboardInterrupt):
            print("\nBye")
            break

        if not message:
            continue

        if message.lower() == "/quit":
            print("Bye")
            break

        result = process_text_message(
            message
        )

        print(
            "\nBot:",
            result.get(
                "text",
                "לא התקבלה תשובה.",
            ),
        )


if __name__ == "__main__":
    main()