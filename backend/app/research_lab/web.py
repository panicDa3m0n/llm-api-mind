"""Bounded public HTTPS retrieval for the Research Lab evidence ledger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import ipaddress
import json
import socket
from typing import Any, Callable
from urllib.parse import urlsplit

import httpx


TRUNCATION_SUFFIX = "\n[Source truncated by Research Lab limit]"


class ResearchLabWebError(ValueError):
    """The requested document is outside the bounded public-web contract."""


@dataclass(frozen=True)
class WebDocument:
    url: str
    title: str | None
    content: str
    content_type: str
    retrieved_at: datetime
    byte_size: int
    content_sha256: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._title_parts: list[str] = []
        self._hidden_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._hidden_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._hidden_depth:
            self._hidden_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in {"p", "div", "br", "li", "section", "article", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._hidden_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
            return
        self._parts.append(data)

    @property
    def title(self) -> str | None:
        value = " ".join("".join(self._title_parts).split())
        return value or None

    @property
    def text(self) -> str:
        return "\n".join(
            line.strip() for line in "".join(self._parts).splitlines() if line.strip()
        )


def fetch_public_web_document(
    url: str,
    *,
    timeout_seconds: float,
    max_bytes: int,
    max_chars: int,
    client: httpx.Client | None = None,
    resolver: Callable[..., Any] = socket.getaddrinfo,
) -> WebDocument:
    parsed = _validate_public_https_url(url, resolver=resolver)
    owns_client = client is None
    active_client = client or httpx.Client(
        timeout=timeout_seconds,
        follow_redirects=False,
        headers={
            "Accept": "text/html, text/plain, application/json;q=0.9",
            "User-Agent": "Scarlet-Research-Lab/1.0 (+bounded-read-only)",
        },
    )
    try:
        with active_client.stream("GET", parsed.geturl()) as response:
            if response.is_redirect:
                raise ResearchLabWebError(
                    "The Research Lab does not follow redirects. Open the final public HTTPS URL explicitly."
                )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";", 1)[0].casefold()
            if content_type not in {"text/html", "text/plain", "application/json"}:
                raise ResearchLabWebError(
                    "Only HTML, plain-text, and JSON documents are accepted as Research Lab sources."
                )
            declared_length = response.headers.get("content-length")
            if declared_length and declared_length.isdigit() and int(declared_length) > max_bytes:
                raise ResearchLabWebError("The source exceeds the Research Lab size limit.")
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise ResearchLabWebError("The source exceeds the Research Lab size limit.")
                chunks.append(chunk)
    except httpx.HTTPError as exc:
        raise ResearchLabWebError("The public source could not be retrieved.") from exc
    finally:
        if owns_client:
            active_client.close()

    raw = b"".join(chunks)
    decoded = raw.decode("utf-8", errors="replace")
    title: str | None = None
    if content_type == "text/html":
        extractor = _TextExtractor()
        extractor.feed(decoded)
        title = extractor.title
        content = extractor.text
    elif content_type == "application/json":
        try:
            content = json.dumps(json.loads(decoded), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            content = decoded
    else:
        content = decoded
    content = content.strip()
    if not content:
        raise ResearchLabWebError("The public source did not contain readable text.")
    content = _truncate(content, max_chars, suffix=TRUNCATION_SUFFIX)
    return WebDocument(
        url=parsed.geturl(),
        title=title,
        content=content,
        content_type=content_type,
        retrieved_at=datetime.now(timezone.utc),
        byte_size=len(raw),
        content_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _validate_public_https_url(
    url: str,
    *,
    resolver: Callable[..., Any],
):
    parsed = urlsplit(url.strip())
    if parsed.scheme.casefold() != "https" or not parsed.hostname:
        raise ResearchLabWebError("Research Lab sources must be public HTTPS URLs.")
    if parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ResearchLabWebError("The URL contains unsupported credentials or port.")
    hostname = parsed.hostname.rstrip(".")
    try:
        addresses = resolver(hostname, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ResearchLabWebError("The public source hostname could not be resolved.") from exc
    if not addresses:
        raise ResearchLabWebError("The public source hostname did not resolve to an address.")
    for item in addresses:
        address = item[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise ResearchLabWebError("The public source hostname returned an invalid address.") from exc
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise ResearchLabWebError("Private or local network sources are not available to Research Lab.")
    return parsed


def _truncate(value: str, limit: int, *, suffix: str) -> str:
    if len(value) <= limit:
        return value
    if limit <= len(suffix):
        return value[:limit]
    return value[: limit - len(suffix)].rstrip() + suffix
