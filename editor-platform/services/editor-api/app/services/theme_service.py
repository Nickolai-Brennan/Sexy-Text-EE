from __future__ import annotations

ALLOWED_KEYS = {
    "fontFamily": "--ed-font-family",
    "fontSize": "--ed-font-size",
    "lineHeight": "--ed-line-height",
    "maxWidth": "--ed-max-width",
    "textColor": "--ed-text-color",
    "linkColor": "--ed-link-color",
    "codeBg": "--ed-code-bg",
    "radius": "--ed-radius",
    "spacing": "--ed-spacing",
}

DEFAULT_TOKENS = {
    "fontFamily": "Inter, system-ui, sans-serif",
    "fontSize": "16px",
    "lineHeight": "1.7",
    "maxWidth": "760px",
    "textColor": "#111111",
    "linkColor": "#0b66ff",
    "codeBg": "#f6f8fa",
    "radius": "10px",
    "spacing": "1rem",
}

def normalize_tokens(tokens: dict | None) -> dict:
    out = dict(DEFAULT_TOKENS)
    if not tokens:
        return out
    for k, v in tokens.items():
        if k in ALLOWED_KEYS and isinstance(v, (str, int, float)):
            out[k] = str(v)
    return out

def tokens_to_scoped_css(tokens: dict | None) -> str:
    t = normalize_tokens(tokens)
    parts = []
    for key, css_var in ALLOWED_KEYS.items():
        parts.append(f"{css_var}:{t.get(key, DEFAULT_TOKENS.get(key,''))}")
    return ".editor-content{" + ";".join(parts) + "}"
