Below are copy/paste **starter code files** (with paths) for the MVP: FastAPI + Strawberry GraphQL + Postgres microservice that:

* stores `content_md` + `style_tokens`
* stores HTML snippets (raw + sanitized)
* renders final `content_html` by injecting snippet HTML into markdown tokens
* returns `themeCss` (scoped CSS vars) + `contentText`

And a React package starter that:

* edits Markdown (Milkdown)
* inserts HTML snippet tokens
* calls GraphQL ops (load/save/render/snippet)
* shows a preview using rendered HTML

---

## services/editor-api

### 1) `services/editor-api/pyproject.toml`

```toml
[project]
name = "editor-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "strawberry-graphql[fastapi]>=0.235",
  "SQLAlchemy>=2.0",
  "asyncpg>=0.29",
  "python-dotenv>=1.0",
  "bleach>=6.1",
  "markdown-it-py>=3.0",
  "beautifulsoup4>=4.12",
]

[tool.uvicorn]
factory = false
```

### 2) `services/editor-api/.env.example`

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/editor
API_KEY=dev-key
ALLOWED_IFRAME_HOSTS=youtube.com,www.youtube.com,youtu.be,player.vimeo.com
```

### 3) `services/editor-api/app/core/config.py`

```python
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/editor")
API_KEY = os.getenv("API_KEY", "dev-key")

ALLOWED_IFRAME_HOSTS = set(
    h.strip() for h in os.getenv(
        "ALLOWED_IFRAME_HOSTS",
        "youtube.com,www.youtube.com,youtu.be,player.vimeo.com",
    ).split(",") if h.strip()
)
```

### 4) `services/editor-api/app/core/security.py`

```python
from fastapi import Header, HTTPException
from app.core.config import API_KEY

async def require_api_key(x_api_key: str | None = Header(default=None)):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True
```

### 5) `services/editor-api/app/db/session.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
```

### 6) `services/editor-api/app/db/base.py`

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

### 7) `services/editor-api/app/models/document.py`

```python
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base
import uuid

class Document(Base):
    __tablename__ = "documents"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_key = sa.Column(sa.Text, unique=True, nullable=False, index=True)
    title = sa.Column(sa.Text, nullable=True)

    content_md = sa.Column(sa.Text, nullable=False, default="")
    content_html = sa.Column(sa.Text, nullable=False, default="")
    content_text = sa.Column(sa.Text, nullable=False, default="")

    style_tokens = sa.Column(JSONB, nullable=False, default=dict)
    theme_key = sa.Column(sa.Text, nullable=False, default="default")

    created_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
```

### 8) `services/editor-api/app/models/snippet.py`

```python
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base
import uuid

class HtmlSnippet(Base):
    __tablename__ = "document_html_snippets"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    name = sa.Column(sa.Text, nullable=True)
    raw_html = sa.Column(sa.Text, nullable=False)
    sanitized_html = sa.Column(sa.Text, nullable=False)
    warnings = sa.Column(JSONB, nullable=False, default=list)

    created_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
```

### 9) `services/editor-api/app/utils/sanitize.py`

```python
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

    cleaned = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        filters=[bleach.sanitizer.Cleaner(tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, protocols=ALLOWED_PROTOCOLS).attributes],
    )

    # Apply attribute-level filter (bleach Cleaner doesn't provide per-attr callback in clean call)
    # So we re-run with Cleaner that supports callbacks:
    cleaner = bleach.Cleaner(
        tags=ALLOWED_TAGS,
        attributes=attr_filter,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    cleaned = cleaner.clean(cleaned)

    # Enforce rel on target=_blank links
    # (simple post-pass)
    cleaned = re.sub(
        r'<a([^>]*?)target="_blank"([^>]*?)>',
        r'<a\1target="_blank"\2 rel="noopener noreferrer">',
        cleaned,
        flags=re.IGNORECASE,
    )

    # Enforce basic sandbox on iframes (post-pass)
    # Note: bleach strips unknown attrs; we keep sandbox out of allowed attrs to avoid author control.
    cleaned = re.sub(
        r"<iframe(.*?)>",
        r'<iframe\1 sandbox="allow-scripts allow-same-origin allow-popups" referrerpolicy="no-referrer">',
        cleaned,
        flags=re.IGNORECASE,
    )

    return cleaned, warnings
```

### 10) `services/editor-api/app/utils/markdown.py`

```python
from markdown_it import MarkdownIt

md = MarkdownIt("commonmark")

def markdown_to_html(markdown: str) -> str:
    return md.render(markdown or "")
```

### 11) `services/editor-api/app/utils/text.py`

```python
from bs4 import BeautifulSoup

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(separator="\n")
    # collapse excessive blank lines
    lines = [ln.rstrip() for ln in text.splitlines()]
    out = []
    for ln in lines:
        if ln == "" and (out and out[-1] == ""):
            continue
        out.append(ln)
    return "\n".join(out).strip()
```

### 12) `services/editor-api/app/services/theme_service.py`

```python
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
```

### 13) `services/editor-api/app/services/render_service.py`

```python
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
```

### 14) `services/editor-api/app/services/document_service.py`

```python
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
```

### 15) `services/editor-api/app/services/snippet_service.py`

```python
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
```

### 16) `services/editor-api/app/graphql/types.py`

```python
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
```

### 17) `services/editor-api/app/graphql/schema.py`

```python
import strawberry
from app.graphql.resolvers import Query, Mutation

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

### 18) `services/editor-api/app/graphql/resolvers.py`

```python
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
```

### 19) `services/editor-api/app/main.py`

```python
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.graphql.schema import schema
from app.graphql.resolvers import get_context
from app.db.session import engine
from app.db.base import Base

app = FastAPI(title="editor-api")

graphql_app = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/health")
async def health():
    return {"ok": True}

# Dev convenience: auto-create tables on startup (replace with Alembic later)
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### 20) `services/editor-api/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

COPY app /app/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## infrastructure

### 21) `infrastructure/docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_USER: postgres
      POSTGRES_DB: editor
    ports:
      - "5432:5432"
    volumes:
      - editor_pgdata:/var/lib/postgresql/data

  editor-api:
    build:
      context: ../services/editor-api
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/editor
      API_KEY: dev-key
      ALLOWED_IFRAME_HOSTS: youtube.com,www.youtube.com,youtu.be,player.vimeo.com
    ports:
      - "8000:8000"
    depends_on:
      - postgres

volumes:
  editor_pgdata:
```

---

## packages/editor-react (Milkdown editor + snippet insert + preview)

### 22) `packages/editor-react/package.json`

```json
{
  "name": "@editor-platform/editor-react",
  "version": "0.1.0",
  "private": true,
  "main": "dist/index.js",
  "module": "dist/index.js",
  "types": "dist/index.d.ts",
  "dependencies": {
    "@milkdown/core": "^7.7.0",
    "@milkdown/react": "^7.7.0",
    "@milkdown/preset-commonmark": "^7.7.0",
    "dompurify": "^3.0.8"
  },
  "devDependencies": {
    "typescript": "^5.5.0"
  }
}
```

### 23) `packages/editor-react/src/api/client.ts`

```ts
export type EditorClientConfig = {
  graphqlUrl: string;      // e.g. http://localhost:8000/graphql
  apiKey: string;          // x-api-key
};

export async function gql<T>(
  cfg: EditorClientConfig,
  query: string,
  variables?: Record<string, any>
): Promise<T> {
  const res = await fetch(cfg.graphqlUrl, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": cfg.apiKey,
    },
    body: JSON.stringify({ query, variables }),
  });

  const json = await res.json();
  if (json.errors?.length) throw new Error(json.errors[0].message);
  return json.data as T;
}
```

### 24) `packages/editor-react/src/api/ops.ts`

```ts
import { gql, EditorClientConfig } from "./client";

export const Q_DOCUMENT = `
  query Doc($documentKey: String!) {
    document(documentKey: $documentKey) {
      documentKey title contentMd styleTokens themeKey
    }
  }
`;

export const M_UPSERT_DOCUMENT = `
  mutation Save($input: UpsertDocumentInput!) {
    upsertDocument(input: $input) {
      documentKey title contentMd styleTokens themeKey updatedAt
    }
  }
`;

export const Q_RENDER = `
  query Render($documentKey: String!) {
    render(documentKey: $documentKey) {
      contentHtml contentText themeCss warnings
    }
  }
`;

export const M_UPSERT_SNIPPET = `
  mutation UpsertSnippet($input: UpsertHtmlSnippetInput!) {
    upsertHtmlSnippet(input: $input) {
      id name rawHtml sanitizedHtml warnings
    }
  }
`;

export type DocumentDTO = {
  documentKey: string;
  title?: string | null;
  contentMd: string;
  styleTokens: any;
  themeKey: string;
};

export async function loadDocument(cfg: EditorClientConfig, documentKey: string) {
  const data = await gql<{ document: DocumentDTO | null }>(cfg, Q_DOCUMENT, { documentKey });
  return data.document;
}

export async function saveDocument(cfg: EditorClientConfig, input: any) {
  const data = await gql<{ upsertDocument: DocumentDTO }>(cfg, M_UPSERT_DOCUMENT, { input });
  return data.upsertDocument;
}

export async function renderDocument(cfg: EditorClientConfig, documentKey: string) {
  const data = await gql<{ render: { contentHtml: string; contentText: string; themeCss: string; warnings: any } }>(
    cfg,
    Q_RENDER,
    { documentKey }
  );
  return data.render;
}

export async function upsertSnippet(cfg: EditorClientConfig, input: any) {
  const data = await gql<{ upsertHtmlSnippet: { id: string; sanitizedHtml: string; warnings: any } }>(
    cfg,
    M_UPSERT_SNIPPET,
    { input }
  );
  return data.upsertHtmlSnippet;
}
```

### 25) `packages/editor-react/src/milkdown/snippetSyntax.ts`

```ts
export function makeSnippetToken(id: string) {
  return `[[html_snippet:${id}]]`;
}
```

### 26) `packages/editor-react/src/components/Preview.tsx`

```tsx
import React from "react";
import DOMPurify from "dompurify";

export function Preview({ html, themeCss }: { html: string; themeCss: string }) {
  const safe = React.useMemo(() => DOMPurify.sanitize(html || ""), [html]);

  return (
    <div>
      <style>{themeCss}</style>
      <div className="editor-content" dangerouslySetInnerHTML={{ __html: safe }} />
    </div>
  );
}
```

### 27) `packages/editor-react/src/components/HtmlSnippetModal.tsx`

```tsx
import React from "react";
import { EditorClientConfig } from "../api/client";
import { upsertSnippet } from "../api/ops";

export function HtmlSnippetModal({
  open,
  onClose,
  cfg,
  documentKey,
  onInserted,
}: {
  open: boolean;
  onClose: () => void;
  cfg: EditorClientConfig;
  documentKey: string;
  onInserted: (snippetId: string) => void;
}) {
  const [rawHtml, setRawHtml] = React.useState(`<div class="callout">Hello</div>`);
  const [warnings, setWarnings] = React.useState<any>(null);
  const [snippetId, setSnippetId] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  if (!open) return null;

  const validateAndSave = async () => {
    setBusy(true);
    try {
      const res = await upsertSnippet(cfg, { documentKey, rawHtml });
      setSnippetId(res.id);
      setWarnings(res.warnings);
    } finally {
      setBusy(false);
    }
  };

  const insert = () => {
    if (!snippetId) return;
    onInserted(snippetId);
    onClose();
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "grid", placeItems: "center" }}>
      <div style={{ width: 820, background: "#fff", padding: 16, borderRadius: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <strong>Insert HTML Snippet</strong>
          <button onClick={onClose}>X</button>
        </div>

        <textarea
          value={rawHtml}
          onChange={(e) => setRawHtml(e.target.value)}
          style={{ width: "100%", height: 220, marginTop: 10, fontFamily: "monospace" }}
        />

        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
          <button onClick={validateAndSave} disabled={busy}>
            {busy ? "Validating..." : "Validate & Save"}
          </button>
          <button onClick={insert} disabled={!snippetId}>
            Insert Into Document
          </button>
        </div>

        {warnings ? (
          <pre style={{ marginTop: 10, background: "#f6f8fa", padding: 10, borderRadius: 10, maxHeight: 120, overflow: "auto" }}>
            {JSON.stringify(warnings, null, 2)}
          </pre>
        ) : null}
      </div>
    </div>
  );
}
```

### 28) `packages/editor-react/src/components/Editor.tsx`

```tsx
import React from "react";
import { MilkdownProvider, useEditor } from "@milkdown/react";
import { Editor as MdEditor } from "@milkdown/core";
import { commonmark } from "@milkdown/preset-commonmark";

import { EditorClientConfig } from "../api/client";
import { loadDocument, saveDocument, renderDocument } from "../api/ops";
import { HtmlSnippetModal } from "./HtmlSnippetModal";
import { Preview } from "./Preview";
import { makeSnippetToken } from "../milkdown/snippetSyntax";

function debounce<T extends (...args: any[]) => void>(fn: T, ms: number) {
  let t: any;
  return (...args: Parameters<T>) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

export function Editor({
  cfg,
  documentKey,
}: {
  cfg: EditorClientConfig;
  documentKey: string;
}) {
  const [title, setTitle] = React.useState("");
  const [md, setMd] = React.useState("");
  const [renderedHtml, setRenderedHtml] = React.useState("");
  const [themeCss, setThemeCss] = React.useState(".editor-content{}");
  const [snippetOpen, setSnippetOpen] = React.useState(false);

  // Load doc
  React.useEffect(() => {
    (async () => {
      const doc = await loadDocument(cfg, documentKey);
      if (doc) {
        setTitle(doc.title || "");
        setMd(doc.contentMd || "");
      } else {
        setTitle("");
        setMd("");
      }
      const r = await renderDocument(cfg, documentKey);
      setRenderedHtml(r.contentHtml);
      setThemeCss(r.themeCss);
    })();
  }, [cfg.graphqlUrl, cfg.apiKey, documentKey]);

  // Milkdown editor
  const editor = useEditor((root) => {
    return MdEditor.make()
      .config((ctx) => {
        // Milkdown react sets root internally; keep minimal here
      })
      .use(commonmark)
      .create();
  });

  // Autosave markdown and refresh preview
  const autosave = React.useMemo(
    () =>
      debounce(async (nextMd: string) => {
        await saveDocument(cfg, {
          documentKey,
          title,
          contentMd: nextMd,
          styleTokens: null,
          themeKey: null,
        });
        const r = await renderDocument(cfg, documentKey);
        setRenderedHtml(r.contentHtml);
        setThemeCss(r.themeCss);
      }, 650),
    [cfg.graphqlUrl, cfg.apiKey, documentKey, title]
  );

  const insertSnippetToken = async (snippetId: string) => {
    const token = makeSnippetToken(snippetId);
    const next = (md || "") + "\n\n" + token + "\n";
    setMd(next);
    await saveDocument(cfg, { documentKey, title, contentMd: next, styleTokens: null, themeKey: null });
    const r = await renderDocument(cfg, documentKey);
    setRenderedHtml(r.contentHtml);
    setThemeCss(r.themeCss);
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      <div>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          style={{ width: "100%", padding: 10, fontSize: 16 }}
        />
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <button onClick={() => setSnippetOpen(true)}>Insert HTML Snippet</button>
        </div>

        <div style={{ marginTop: 10, border: "1px solid #ddd", borderRadius: 10, padding: 10, minHeight: 360 }}>
          {/* Simple textarea for md state bridge (Milkdown hookup varies by integration) */}
          <textarea
            value={md}
            onChange={(e) => {
              const next = e.target.value;
              setMd(next);
              autosave(next);
            }}
            style={{ width: "100%", height: 340, fontFamily: "monospace", border: 0, outline: "none" }}
          />
        </div>

        {/* Milkdown UI placeholder (wire later once you decide exact Milkdown React pattern) */}
        <div style={{ marginTop: 10, opacity: 0.7, fontSize: 12 }}>
          Milkdown can replace the textarea once you finalize the editor binding strategy.
        </div>
      </div>

      <div>
        <div style={{ border: "1px solid #ddd", borderRadius: 10, padding: 10, minHeight: 420 }}>
          <Preview html={renderedHtml} themeCss={themeCss} />
        </div>
      </div>

      <HtmlSnippetModal
        open={snippetOpen}
        onClose={() => setSnippetOpen(false)}
        cfg={cfg}
        documentKey={documentKey}
        onInserted={insertSnippetToken}
      />
    </div>
  );
}
```

### 29) `packages/editor-react/src/index.ts`

```ts
export * from "./components/Editor";
export type { EditorClientConfig } from "./api/client";
```

> Note: I used a textarea as the initial markdown editor to keep the starter “runs immediately” while you finalize Milkdown binding. Once you choose your exact Milkdown React integration pattern, swap the textarea with Milkdown’s editor view and feed updates into the same `autosave()` pipeline.

---

## Quick run steps (local)

1. Start API + Postgres

```bash
cd infrastructure
docker compose up --build
```

2. Test GraphQL quickly (curl)

```bash
curl -s http://localhost:8000/graphql \
  -H "content-type: application/json" \
  -H "x-api-key: dev-key" \
  -d '{"query":"{ render(documentKey:\"siteA:blog:post:demo\"){ contentHtml themeCss warnings } }"}' | jq
```

3. Add a playground app (or import `@editor-platform/editor-react` into your site) and use:

* `graphqlUrl: "http://localhost:8000/graphql"`
* `apiKey: "dev-key"`
* `documentKey: "siteA:blog:post:demo"`

---

## What I’ll generate next if you want it (same style: starter files)

* Full **Milkdown** binding (replace textarea) with: toolbar, commands, markdown get/set, proper onChange
* Alembic migrations (instead of `create_all`)
* Media upload endpoints + `<img>` insertion
* ThemePanel UI + saving `styleTokens` into the microservice
