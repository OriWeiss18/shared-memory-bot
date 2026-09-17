import ipaddress
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


URL_PATTERN = re.compile(r"https?://[^\s]+")
MAX_EXTRACTED_TEXT_LENGTH = 20_000


def extract_url(text: str) -> str | None:
    """
    Extract the first http/https URL from a text message.
    """
    match = URL_PATTERN.search(text)

    if not match:
        return None

    url = match.group(0)

    return url.rstrip(".,!?;:)]}")


def validate_url(url: str) -> None:
    """
    Basic protection against fetching local/private addresses.
    """
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported")

    hostname = parsed.hostname

    if not hostname:
        raise ValueError("URL has no hostname")

    if hostname.lower() == "localhost":
        raise ValueError("Local URLs are not allowed")

    try:
        ip = ipaddress.ip_address(hostname)

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
        ):
            raise ValueError("Private/local IP addresses are not allowed")

    except ValueError as exc:
        if "Private/local" in str(exc):
            raise


def extract_page_content(html: str) -> tuple[str | None, str]:
    """
    Extract a page title and useful visible text from HTML.
    """
    soup = BeautifulSoup(html, "html.parser")

    title = None

    if soup.title:
        title = soup.title.get_text(" ", strip=True) or None

    # Remove elements that normally do not contain useful saved content.
    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "nav",
            "header",
            "footer",
            "aside",
            "form",
            "svg",
        ]
    ):
        tag.decompose()

    # Prefer the main/article content when the page provides it.
    content = (
        soup.find("article")
        or soup.find("main")
        or soup.body
        or soup
    )

    text = content.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > MAX_EXTRACTED_TEXT_LENGTH:
        text = text[:MAX_EXTRACTED_TEXT_LENGTH]

    return title, text


def fetch_url_content(url: str) -> dict:
    """
    Download a webpage and extract its title and visible text.
    """
    validate_url(url)

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SharedMemoryBot/1.0)"
    }

    response = httpx.get(
        url,
        headers=headers,
        timeout=15.0,
        follow_redirects=True,
    )

    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()

    if "text/html" not in content_type:
        raise ValueError(
            f"Unsupported content type: {content_type or 'unknown'}"
        )

    title, text = extract_page_content(response.text)

    return {
        "url": str(response.url),
        "title": title,
        "text": text,
    }
