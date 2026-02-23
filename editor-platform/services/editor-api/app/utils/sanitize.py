from __future__ import annotations
import re
from urllib.parse import urlparse
import bleach
from app.core.config import ALLOWED_IFRAME_HOSTS

ALLOWED_TAGS = [
    # structure
    "div", "span", "p", "br", "hr", "blockquote",
    # headings
    "h1","h2","h3","h4","h5","h6",
    # inline
    "strong","em","u","s","code",
    # lists
    "ul","ol","li",
    # code blocks
    "pre","code",
    # links/images
    "a","img","figure","figcaption",
    # tables
    "table","thead","tbody","tr","th","td",
    # embeds
    "iframe",
]

ALLOWED_ATTRS = {
    "*": ["class", "id", "title", "aria-*", "data-*"],
    "a": ["href", "target", "rel"],
    "img": ["src", "alt", "width", "height", "loading"],
    "iframe": ["src", "width", "height", "allow", "allowfullscreen", "frameborder", "title"],
    "th": ["colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
}

ALLOWED_PROTOCOLS = ["http", "https", "data"]

EVENT_HANDLER_RE = re.compile(r"^on[a-z]+$", re.IGNORECASE)

def _is_allowed_iframe_src(src: str) -> bool:
    try:
        host = (urlparse(src).hostname or "").lower()
        return host in ALLOWED_IFRAME_HOSTS
    except Exception:
        return False

def sanitize_html(raw_html: str) -> tuple[str, list[dict]]:
    warnings: list[dict] = []

    # Quick warnings for obvious bad stuff
    if "<script" in raw_html.lower():
        warnings.append({"code": "SCRIPT_STRIPPED", "message": "Script tags are not allowed and were stripped."})

    def attr_filter(tag, name, value):
        # strip inline event handlers
        if EVENT_HANDLER_RE.match(name):
            warnings.append({"code": "EVENT_HANDLER_STRIPPED", "message": f"Removed unsafe attribute: {name}"})
            return None

        # iframe src allowlist
        if tag == "iframe" and name == "src":
            if not _is_allowed_iframe_src(value):
                warnings.append({"code": "IFRAME_BLOCKED", "message": "Iframe src host not allowed."})
                return None
        return value

    cleaner = bleach.Cleaner(
        tags=ALLOWED_TAGS,
        attributes=attr_filter,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    cleaned = cleaner.clean(raw_html or "")

    # Enforce rel on target=_blank links
    cleaned = re.sub(
        r'<a([^>]*?)target="_blank"([^>]*?)>',
        r'<a\1target="_blank"\2 rel="noopener noreferrer">',
        cleaned,
        flags=re.IGNORECASE,
    )

    # Enforce basic sandbox on iframes (post-pass)
    cleaned = re.sub(
        r"<iframe(.*?)>",
        r'<iframe\1 sandbox="allow-scripts allow-same-origin allow-popups" referrerpolicy="no-referrer">',
        cleaned,
        flags=re.IGNORECASE,
    )

    return cleaned, warnings
