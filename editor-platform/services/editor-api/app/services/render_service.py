from __future__ import annotations
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.snippet import HtmlSnippet
from app.utils.markdown import markdown_to_html
from app.utils.sanitize import sanitize_html
from app.utils.text import html_to_text
from app.services.theme_service import tokens_to_scoped_css

SNIP_RE = re.compile(r"\[\[html_snippet:([0-9a-fA-F-]{36})\]\]")

async def _load_document(db: AsyncSession, document_key: str) -> Document | None:
    res = await db.execute(select(Document).where(Document.document_key == document_key))
    return res.scalar_one_or_none()

async def _snippet_map(db: AsyncSession, document_id) -> dict[str, HtmlSnippet]:
    res = await db.execute(select(HtmlSnippet).where(HtmlSnippet.document_id == document_id))
    rows = res.scalars().all()
    return {str(s.id): s for s in rows}

def _inject_snippets(md: str, snippets: dict[str, HtmlSnippet], warnings: list[dict]) -> str:
    def repl(match: re.Match) -> str:
        sid = match.group(1)
        snip = snippets.get(sid)
        if not snip:
            warnings.append({"code": "MISSING_SNIPPET", "message": f"Missing snippet: {sid}"})
            return ""
        # Inject as raw HTML block
        return f"\n\n{snip.sanitized_html}\n\n"
    return SNIP_RE.sub(repl, md or "")

async def render_document(db: AsyncSession, document_key: str) -> dict:
    warnings: list[dict] = []

    doc = await _load_document(db, document_key)
    if not doc:
        return {
            "contentHtml": "",
            "contentText": "",
            "themeCss": tokens_to_scoped_css(None),
            "warnings": [{"code": "NOT_FOUND", "message": "Document not found"}],
        }

    snippets = await _snippet_map(db, doc.id)
    md_with_snips = _inject_snippets(doc.content_md, snippets, warnings)

    html = markdown_to_html(md_with_snips)

    # Final safety pass (important)
    html_sanitized, w2 = sanitize_html(html)
    warnings.extend(w2)

    text = html_to_text(html_sanitized)
    theme_css = tokens_to_scoped_css(doc.style_tokens)

    # Persist derived fields (optional but useful)
    doc.content_html = html_sanitized
    doc.content_text = text
    await db.commit()

    return {
        "contentHtml": html_sanitized,
        "contentText": text,
        "themeCss": theme_css,
        "warnings": warnings,
    }
