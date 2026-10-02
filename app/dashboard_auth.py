import base64
import hashlib
import hmac
import json
import os
import time


TOKEN_LIFETIME_SECONDS = 60 * 60 * 24


def _get_secret() -> str:
    secret = os.getenv("DASHBOARD_LINK_SECRET")

    if not secret:
        raise RuntimeError(
            "DASHBOARD_LINK_SECRET is not configured"
        )

    return secret


def _encode(data: bytes) -> str:
    return (
        base64.urlsafe_b64encode(data)
        .decode("utf-8")
        .rstrip("=")
    )


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)

    return base64.urlsafe_b64decode(
        value + padding
    )


def create_dashboard_token(
    user_id: str,
) -> str:
    payload = {
        "user_id": user_id,
        "expires_at": (
            int(time.time())
            + TOKEN_LIFETIME_SECONDS
        ),
    }

    payload_bytes = json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")

    encoded_payload = _encode(
        payload_bytes
    )

    signature = hmac.new(
        _get_secret().encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return (
        f"{encoded_payload}."
        f"{_encode(signature)}"
    )


def verify_dashboard_token(
    token: str,
) -> str | None:
    try:
        encoded_payload, encoded_signature = (
            token.split(".", 1)
        )

        expected_signature = hmac.new(
            _get_secret().encode("utf-8"),
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        provided_signature = _decode(
            encoded_signature
        )

        if not hmac.compare_digest(
            expected_signature,
            provided_signature,
        ):
            return None

        payload = json.loads(
            _decode(
                encoded_payload
            ).decode("utf-8")
        )

        if payload["expires_at"] < time.time():
            return None

        return payload["user_id"]

    except (
        ValueError,
        KeyError,
        json.JSONDecodeError,
        RuntimeError,
    ):
        return None
