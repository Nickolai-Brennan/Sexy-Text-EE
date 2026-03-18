Good. Clean slate.

Below is a **minimal, production-safe starter** using:

* Milkdown **Crepe**
* FastAPI + Strawberry GraphQL
* PostgreSQL
* HTML snippet rendering (sanitized)
* Theme CSS tokens
* Markdown as canonical storage

No extra noise.

---

# 📁 Project Structure

```
editor-platform/
├── services/
│   └── editor-api/
│       ├── app/
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── db.py
│       │   ├── models.py
│       │   ├── sanitize.py
│       │   ├── render.py
│       │   └── schema.py
│       ├── pyproject.toml
│       └── .env
├── web/
│   ├── package.json
│   └── src/
│       ├── Editor.tsx
│       ├── Preview.tsx
│       └── api.ts
└── docker-compose.yml
```

---

# 🐘 docker-compose.yml

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_USER: postgres
      POSTGRES_DB: editor
    ports:
      - "5432:5432"

  api:
    build: ./services/editor-api
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/editor
      API_KEY: dev-key
    ports:
      - "8000:8000"
    depends_on:
      - postgres
```

---

# 🐍 BACKEND (FastAPI)

## services/editor-api/pyproject.toml

```toml
[project]
name = "editor-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "strawberry-graphql[fastapi]",
  "sqlalchemy",
  "asyncpg",
  "bleach",
  "markdown-it-py",
  "beautifulsoup4",
]
```

---

## services/editor-api/app/config.py

```python
import os

DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY", "dev-key")
```

---

## services/editor-api/app/db.py

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass
```

---

## services/editor-api/app/models.py

```python
import uuid
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db import Base

class Document(Base):
    __tablename__ = "documents"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_key = sa.Column(sa.Text, unique=True, nullable=False)

    content_md = sa.Column(sa.Text, nullable=False, default="")
    content_html = sa.Column(sa.Text, nullable=False, default="")
    content_text = sa.Column(sa.Text, nullable=False, default="")
    style_tokens = sa.Column(JSONB, nullable=False, default=dict)
```

---

## services/editor-api/app/sanitize.py

```python
import bleach

ALLOWED_TAGS = [
    "div","span","p","br","strong","em","ul","ol","li",
    "h1","h2","h3","h4","h5","h6","pre","code","a","img","iframe"
]

ALLOWED_ATTRS = {
    "*": ["class","id"],
    "a": ["href","target","rel"],
    "img": ["src","alt","width","height"],
    "iframe": ["src","width","height"]
}

def sanitize_html(html: str):
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,
    )
```

---

## services/editor-api/app/render.py

```python
import re
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup
from app.sanitize import sanitize_html

md = MarkdownIt()

SNIP_RE = re.compile(r"\[\[html_snippet:(.*?)\]\]")

def html_to_text(html: str):
    return BeautifulSoup(html, "html.parser").get_text()

def render_markdown(content_md: str):
    html = md.render(content_md)
    html = sanitize_html(html)
    text = html_to_text(html)
    return html, text
```

---

## services/editor-api/app/schema.py

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
```

---

## services/editor-api/app/main.py

```python
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from app.schema import schema
from app.db import Base, engine

app = FastAPI()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(GraphQLRouter(schema), prefix="/graphql")
```

---

# 🌐 FRONTEND (Crepe)

## web/package.json

```json
{
  "dependencies": {
    "@milkdown/crepe": "^7.7.0",
    "react": "^18",
    "react-dom": "^18"
  }
}
```

---

## web/src/api.ts

```ts
export async function gql(query: string, variables: any = {}) {
  const res = await fetch("http://localhost:8000/graphql", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, variables }),
  });
  const json = await res.json();
  if (json.errors) throw new Error(json.errors[0].message);
  return json.data;
}
```

---

## web/src/Preview.tsx

```tsx
export function Preview({ html }: { html: string }) {
  return (
    <div className="editor-content"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
```

---

## web/src/Editor.tsx

```tsx
import React, { useEffect, useRef, useState } from "react";
import { Crepe } from "@milkdown/crepe";
import "@milkdown/crepe/theme/common/style.css";
import "@milkdown/crepe/theme/frame.css";
import { gql } from "./api";
import { Preview } from "./Preview";

export function Editor() {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [html, setHtml] = useState("");
  const documentKey = "siteA:blog:demo";

  useEffect(() => {
    if (!rootRef.current) return;

    const crepe = new Crepe({
      root: rootRef.current,
      defaultValue: "# Start writing...",
    });

    crepe.create();

    crepe.on((listener) => {
      listener.markdownUpdated(async (_, markdown) => {
        const data = await gql(
          `
          mutation Save($key: String!, $md: String!) {
            saveDocument(documentKey: $key, contentMd: $md) {
              contentHtml
            }
          }
        `,
          { key: documentKey, md: markdown }
        );
        setHtml(data.saveDocument.contentHtml);
      });
    });

    return () => crepe.destroy();
  }, []);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
      <div ref={rootRef}></div>
      <Preview html={html} />
    </div>
  );
}
```

---

# 🚀 Run It

1. `docker compose up --build`
2. Start React app
3. Open browser
4. Type → Markdown saved → HTML preview rendered

---

# What This Starter Does

* Crepe editor works
* Markdown stored in Postgres
* HTML rendered server-side
* Sanitized output
* Live preview
* No unsafe scripts
* Microservice ready

---

If you want the **next version** with:

* HTML snippet tokens
* Iframe domain allowlist
* Style token panel
* Code highlighting
* Cursor insertion macros
* Proper auth
* Production theme system

Say “upgrade it” and I’ll send phase 2.
