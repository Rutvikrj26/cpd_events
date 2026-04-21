"""HTML sanitization and mention extraction for discussion posts."""

from __future__ import annotations

import re
import uuid as uuid_lib

import bleach

ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "s", "code", "pre", "blockquote",
    "ul", "ol", "li", "a", "h3", "h4", "span",
]

ALLOWED_ATTRS = {
    "a": ["href", "title", "rel", "target"],
    "span": ["class", "data-user-uuid", "data-user-email", "data-denotation-char", "data-id", "data-value"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

_MENTION_SPAN_RE = re.compile(
    r'<span[^>]*class="[^"]*\bmention\b[^"]*"[^>]*data-user-uuid="([^"]+)"[^>]*>',
    re.IGNORECASE,
)


def clean_discussion_html(html: str) -> tuple[str, str]:
    """Sanitize Quill-produced HTML and return (cleaned_html, plain_text)."""
    if not html:
        return "", ""
    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    plain = bleach.clean(cleaned, tags=[], strip=True).strip()
    return cleaned, plain


def extract_mentions(html: str) -> list[str]:
    """Return unique user UUIDs referenced by <span class="mention" data-user-uuid="..."> tags."""
    if not html:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for match in _MENTION_SPAN_RE.finditer(html):
        raw = match.group(1).strip()
        try:
            normalized = str(uuid_lib.UUID(raw))
        except (ValueError, AttributeError):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
