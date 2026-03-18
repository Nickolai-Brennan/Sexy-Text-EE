```python
import strawberry
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Document
from app.render import render_markdown

@strawberry.type
class DocumentType:
    documentKey: str
    contentMd: str
    contentHtml: str
    contentText: str

@strawberry.type
class Query:
    @strawberry.field
    async def document(self, documentKey: str) -> DocumentType | None:
        async with SessionLocal() as db:
            res = await db.execute(select(Document).where(Document.document_key == documentKey))
            doc = res.scalar_one_or_none()
            if not doc:
                return None
            return DocumentType(
                documentKey=doc.document_key,
                contentMd=doc.content_md,
                contentHtml=doc.content_html,
                contentText=doc.content_text,
            )

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def saveDocument(self, documentKey: str, contentMd: str) -> DocumentType:
        async with SessionLocal() as db:
            res = await db.execute(select(Document).where(Document.document_key == documentKey))
            doc = res.scalar_one_or_none()
            if not doc:
                doc = Document(document_key=documentKey)
                db.add(doc)

            html, text = render_markdown(contentMd)
            doc.content_md = contentMd
            doc.content_html = html
            doc.content_text = text

            await db.commit()
            await db.refresh(doc)

            return DocumentType(
                documentKey=doc.document_key,
                contentMd=doc.content_md,
                contentHtml=doc.content_html,
                contentText=doc.content_text,
            )

schema = strawberry.Schema(query=Query, mutation=Mutation)