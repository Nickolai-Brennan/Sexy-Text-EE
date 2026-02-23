from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.snippet import HtmlSnippet
from app.utils.sanitize import sanitize_html

async def _get_doc(db: AsyncSession, document_key: str) -> Document | None:
    res = await db.execute(select(Document).where(Document.document_key == document_key))
    return res.scalar_one_or_none()

async def list_snippets(db: AsyncSession, document_key: str) -> list[HtmlSnippet]:
    doc = await _get_doc(db, document_key)
    if not doc:
        return []
    res = await db.execute(select(HtmlSnippet).where(HtmlSnippet.document_id == doc.id))
    return list(res.scalars().all())

async def upsert_snippet(db: AsyncSession, document_key: str, snippet_id: str | None, name: str | None, raw_html: str) -> HtmlSnippet:
    doc = await _get_doc(db, document_key)
    if not doc:
        doc = Document(document_key=document_key, content_md="")
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

    sanitized, warnings = sanitize_html(raw_html or "")

    snippet: HtmlSnippet | None = None
    if snippet_id:
        res = await db.execute(select(HtmlSnippet).where(HtmlSnippet.id == snippet_id, HtmlSnippet.document_id == doc.id))
        snippet = res.scalar_one_or_none()

    if not snippet:
        snippet = HtmlSnippet(document_id=doc.id, raw_html=raw_html or "", sanitized_html=sanitized, warnings=warnings, name=name)
        db.add(snippet)
    else:
        snippet.name = name
        snippet.raw_html = raw_html or ""
        snippet.sanitized_html = sanitized
        snippet.warnings = warnings

    await db.commit()
    await db.refresh(snippet)
    return snippet

async def delete_snippet(db: AsyncSession, document_key: str, snippet_id: str) -> bool:
    doc = await _get_doc(db, document_key)
    if not doc:
        return False
    res = await db.execute(select(HtmlSnippet).where(HtmlSnippet.id == snippet_id, HtmlSnippet.document_id == doc.id))
    snippet = res.scalar_one_or_none()
    if not snippet:
        return False
    await db.delete(snippet)
    await db.commit()
    return True
