from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document

async def get_document(db: AsyncSession, document_key: str) -> Document | None:
    res = await db.execute(select(Document).where(Document.document_key == document_key))
    return res.scalar_one_or_none()

async def upsert_document(db: AsyncSession, document_key: str, title: str | None, content_md: str, style_tokens: dict | None, theme_key: str | None) -> Document:
    doc = await get_document(db, document_key)
    if not doc:
        doc = Document(document_key=document_key)
        db.add(doc)

    doc.title = title
    doc.content_md = content_md or ""
    if style_tokens is not None and isinstance(style_tokens, dict):
        doc.style_tokens = style_tokens
    if theme_key:
        doc.theme_key = theme_key

    await db.commit()
    await db.refresh(doc)
    return doc
