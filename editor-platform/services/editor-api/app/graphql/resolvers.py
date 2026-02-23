import strawberry
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from strawberry.fastapi import BaseContext

from app.db.session import get_db
from app.core.security import require_api_key
from app.graphql.types import (
    DocumentType, HtmlSnippetType, RenderResultType,
    UpsertDocumentInput, UpsertHtmlSnippetInput
)
from app.services.document_service import get_document, upsert_document
from app.services.snippet_service import list_snippets, upsert_snippet, delete_snippet
from app.services.render_service import render_document

class Context(BaseContext):
    db: AsyncSession

async def get_context(db: AsyncSession = Depends(get_db), _=Depends(require_api_key)) -> Context:
    ctx = Context()
    ctx.db = db
    return ctx

def _doc_to_type(d) -> DocumentType:
    return DocumentType(
        id=str(d.id),
        documentKey=d.document_key,
        title=d.title,
        contentMd=d.content_md,
        contentHtml=d.content_html,
        contentText=d.content_text,
        styleTokens=d.style_tokens,
        themeKey=d.theme_key,
        createdAt=d.created_at,
        updatedAt=d.updated_at,
    )

def _snip_to_type(s) -> HtmlSnippetType:
    return HtmlSnippetType(
        id=str(s.id),
        documentId=str(s.document_id),
        name=s.name,
        rawHtml=s.raw_html,
        sanitizedHtml=s.sanitized_html,
        warnings=s.warnings,
        createdAt=s.created_at,
        updatedAt=s.updated_at,
    )

@strawberry.type
class Query:
    @strawberry.field
    async def document(self, info: strawberry.Info[Context], documentKey: str) -> DocumentType | None:
        d = await get_document(info.context.db, documentKey)
        return _doc_to_type(d) if d else None

    @strawberry.field
    async def snippets(self, info: strawberry.Info[Context], documentKey: str) -> list[HtmlSnippetType]:
        rows = await list_snippets(info.context.db, documentKey)
        return [_snip_to_type(r) for r in rows]

    @strawberry.field
    async def render(self, info: strawberry.Info[Context], documentKey: str) -> RenderResultType:
        res = await render_document(info.context.db, documentKey)
        return RenderResultType(
            contentHtml=res["contentHtml"],
            contentText=res["contentText"],
            themeCss=res["themeCss"],
            warnings=res["warnings"],
        )

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def upsertDocument(self, info: strawberry.Info[Context], input: UpsertDocumentInput) -> DocumentType:
        d = await upsert_document(
            info.context.db,
            document_key=input.documentKey,
            title=input.title,
            content_md=input.contentMd,
            style_tokens=input.styleTokens if isinstance(input.styleTokens, dict) else (input.styleTokens or None),
            theme_key=input.themeKey,
        )
        return _doc_to_type(d)

    @strawberry.mutation
    async def upsertHtmlSnippet(self, info: strawberry.Info[Context], input: UpsertHtmlSnippetInput) -> HtmlSnippetType:
        s = await upsert_snippet(
            info.context.db,
            document_key=input.documentKey,
            snippet_id=str(input.snippetId) if input.snippetId else None,
            name=input.name,
            raw_html=input.rawHtml,
        )
        return _snip_to_type(s)

    @strawberry.mutation
    async def deleteHtmlSnippet(self, info: strawberry.Info[Context], documentKey: str, snippetId: strawberry.ID) -> bool:
        return await delete_snippet(info.context.db, documentKey, str(snippetId))
