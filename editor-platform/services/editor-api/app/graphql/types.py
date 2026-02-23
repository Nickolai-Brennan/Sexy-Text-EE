import strawberry
from typing import Any, Optional, List
from datetime import datetime

JSON = strawberry.scalar(
    Any,
    name="JSON",
    serialize=lambda v: v,
    parse_value=lambda v: v,
)

@strawberry.type
class DocumentType:
    id: strawberry.ID
    documentKey: str
    title: Optional[str]
    contentMd: str
    contentHtml: str
    contentText: str
    styleTokens: JSON
    themeKey: str
    createdAt: datetime
    updatedAt: datetime

@strawberry.type
class HtmlSnippetType:
    id: strawberry.ID
    documentId: strawberry.ID
    name: Optional[str]
    rawHtml: str
    sanitizedHtml: str
    warnings: JSON
    createdAt: datetime
    updatedAt: datetime

@strawberry.type
class RenderResultType:
    contentHtml: str
    contentText: str
    themeCss: str
    warnings: JSON

@strawberry.input
class UpsertDocumentInput:
    documentKey: str
    title: Optional[str] = None
    contentMd: str = ""
    styleTokens: Optional[JSON] = None
    themeKey: Optional[str] = None

@strawberry.input
class UpsertHtmlSnippetInput:
    documentKey: str
    snippetId: Optional[strawberry.ID] = None
    name: Optional[str] = None
    rawHtml: str = ""
