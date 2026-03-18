Continuing from the “start-over minimal” version: here’s the **next set of files** that upgrades it to the real MVP you asked for:

* Render **HTML snippets as HTML** (sanitized, iframe allowlist)
* Store snippets in Postgres
* Inject snippet tokens into markdown: `[[html_snippet:<uuid>]]`
* Return `themeCss` (scoped CSS vars) + `contentHtml` + `contentText`
* Add API key auth on `/graphql`
* Crepe editor initialized after loading server markdown, with cursor insertion using Milkdown’s `insert(...)` macro ([milkdown.dev][1])

Everything below is **full file content** (copy/paste). Overwrite existing ones where paths match.

---

## 1) BACKEND UPGRADE (services/editor-api)

### `services/editor-api/app/models.py` (REPLACE)

```python
import uuid
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db import Base

class Document(Base):
    __tablename__ = "documents"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_key = sa.Column(sa.Text, unique=True, nullable=False, index=True)

    content_md = sa.Column(sa.Text, nullable=False, default="")
    content_html = sa.Column(sa.Text, nullable=False, default="")
    content_text = sa.Column(sa.Text, nullable=False, default="")

    style_tokens = sa.Column(JSONB, nullable=False, default=dict)
    theme_key = sa.Column(sa.Text, nullable=False, default="default")

    created_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

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

### `services/editor-api/app/security.py` (NEW)

```python
from fastapi import Header, HTTPException
from app.config import API_KEY

async def require_api_key(x_api_key: str | None = Header(default=None)):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True
```

### `services/editor-api/app/sanitize.py` (REPLACE)

Adds iframe allowlist + sandbox enforcement + strips event handlers.

```python
from __future__ import annotations
import re
from urllib.parse import urlparse
import bleach

ALLOWED_IFRAME_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "player.vimeo.com",
}

ALLOWED_TAGS = [
    "div","span","p","br","hr","blockquote",
    "h1","h2","h3","h4","h5","h6",
    "strong","em","u","s","code",
    "ul","ol","li",
    "pre","code",
    "a","img","figure","figcaption",
    "table","thead","tbody","tr","th","td",
    "iframe",
]

ALLOWED_ATTRS = {
    "*": ["class","id","title","aria-*","data-*"],
    "a": ["href","target","rel"],
    "img": ["src","alt","width","height","loading"],
    "iframe": ["src","width","height","allow","allowfullscreen","frameborder","title"],
    "th": ["colspan","rowspan"],
    "td": ["colspan","rowspan"],
}

ALLOWED_PROTOCOLS = ["http","https","data"]
EVENT_HANDLER_RE = re.compile(r"^on[a-z]+$", re.IGNORECASE)

def _iframe_allowed(src: str) -> bool:
    try:
        host = (urlparse(src).hostname or "").lower()
        return host in ALLOWED_IFRAME_HOSTS
    except Exception:
        return False

def sanitize_html(raw_html: str) -> tuple[str, list[dict]]:
    warnings: list[dict] = []

    def attr_filter(tag, name, value):
        if EVENT_HANDLER_RE.match(name):
            warnings.append({"code": "EVENT_HANDLER_STRIPPED", "message": f"Removed {name}"})
            return None
        if tag == "iframe" and name == "src":
            if not _iframe_allowed(value):
                warnings.append({"code": "IFRAME_BLOCKED", "message": "Iframe host not allowed"})
                return None
        return value

    cleaner = bleach.Cleaner(
        tags=ALLOWED_TAGS,
        attributes=attr_filter,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    cleaned = cleaner.clean(raw_html or "")

    # Force rel for target=_blank
    cleaned = re.sub(
        r'<a([^>]*?)target="_blank"([^>]*?)>',
        r'<a\1target="_blank"\2 rel="noopener noreferrer">',
        cleaned,
        flags=re.IGNORECASE,
    )

    # Force sandbox on iframes (authors cannot control it)
    cleaned = re.sub(
        r"<iframe(.*?)>",
        r'<iframe\1 sandbox="allow-scripts allow-same-origin allow-popups" referrerpolicy="no-referrer">',
        cleaned,
        flags=re.IGNORECASE,
    )

    return cleaned, warnings
```

### `services/editor-api/app/theme.py` (NEW)

```python
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
    parts = [f"{ALLOWED_KEYS[k]}:{t.get(k, DEFAULT_TOKENS[k])}" for k in ALLOWED_KEYS]
    return ".editor-content{" + ";".join(parts) + "}"
```

### `services/editor-api/app/render.py` (REPLACE)

Token injection + markdown render + final sanitize pass + themeCss.

```python
from __future__ import annotations
import re
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup

from app.sanitize import sanitize_html
from app.theme import tokens_to_scoped_css

md = MarkdownIt("commonmark")

SNIP_RE = re.compile(r"\[\[html_snippet:([0-9a-fA-F-]{36})\]\]")

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(separator="\n")
    lines = [ln.rstrip() for ln in text.splitlines()]
    out = []
    for ln in lines:
        if ln == "" and (out and out[-1] == ""):
            continue
        out.append(ln)
    return "\n".join(out).strip()

def inject_snippets(markdown: str, snippet_map: dict[str, str], warnings: list[dict]) -> str:
    def repl(match: re.Match) -> str:
        sid = match.group(1)
        html = snippet_map.get(sid)
        if not html:
            warnings.append({"code": "MISSING_SNIPPET", "message": f"Missing snippet {sid}"})
            return ""
        return f"\n\n{html}\n\n"
    return SNIP_RE.sub(repl, markdown or "")

def render_markdown(content_md: str, snippet_map: dict[str, str], style_tokens: dict | None) -> dict:
    warnings: list[dict] = []

    md_with_snips = inject_snippets(content_md, snippet_map, warnings)
    html = md.render(md_with_snips)

    html_sanitized, w2 = sanitize_html(html)
    warnings.extend(w2)

    text = html_to_text(html_sanitized)
    theme_css = tokens_to_scoped_css(style_tokens)

    return {
        "contentHtml": html_sanitized,
        "contentText": text,
        "themeCss": theme_css,
        "warnings": warnings,
    }
```

### `services/editor-api/app/schema.py` (REPLACE)

Adds snippets + render query + styleTokens.

```python
import strawberry
from typing import Any, Optional
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Document, HtmlSnippet
from app.render import render_markdown

JSON = strawberry.scalar(
    Any,
    name="JSON",
    serialize=lambda v: v,
    parse_value=lambda v: v,
)

@strawberry.type
class HtmlSnippetType:
    id: strawberry.ID
    name: Optional[str]
    rawHtml: str
    sanitizedHtml: str
    warnings: JSON

@strawberry.type
class DocumentType:
    documentKey: str
    contentMd: str
    styleTokens: JSON
    themeKey: str

@strawberry.type
class RenderResultType:
    contentHtml: str
    contentText: str
    themeCss: str
    warnings: JSON

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
                styleTokens=doc.style_tokens,
                themeKey=doc.theme_key,
            )

    @strawberry.field
    async def snippets(self, documentKey: str) -> list[HtmlSnippetType]:
        async with SessionLocal() as db:
            res = await db.execute(select(Document).where(Document.document_key == documentKey))
            doc = res.scalar_one_or_none()
            if not doc:
                return []
            res2 = await db.execute(select(HtmlSnippet).where(HtmlSnippet.document_id == doc.id))
            rows = res2.scalars().all()
            return [
                HtmlSnippetType(
                    id=str(s.id),
                    name=s.name,
                    rawHtml=s.raw_html,
                    sanitizedHtml=s.sanitized_html,
                    warnings=s.warnings,
                )
                for s in rows
            ]

    @strawberry.field
    async def render(self, documentKey: str) -> RenderResultType:
        async with SessionLocal() as db:
            res = await db.execute(select(Document).where(Document.document_key == documentKey))
            doc = res.scalar_one_or_none()
            if not doc:
                empty = render_markdown("", {}, None)
                return RenderResultType(**empty)

            res2 = await db.execute(select(HtmlSnippet).where(HtmlSnippet.document_id == doc.id))
            snippets = res2.scalars().all()
            snippet_map = {str(s.id): s.sanitized_html for s in snippets}

            out = render_markdown(doc.content_md, snippet_map, doc.style_tokens)

            # persist derived fields
            doc.content_html = out["contentHtml"]
            doc.content_text = out["contentText"]
            await db.commit()

            return RenderResultType(**out)

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def saveDocument(
        self,
        documentKey: str,
        contentMd: str,
        styleTokens: Optional[JSON] = None,
        themeKey: Optional[str] = None,
    ) -> DocumentType:
        async with SessionLocal() as db:
            res = await db.execute(select(Document).where(Document.document_key == documentKey))
            doc = res.scalar_one_or_none()
            if not doc:
                doc = Document(document_key=documentKey)
                db.add(doc)

            doc.content_md = contentMd or ""
            if isinstance(styleTokens, dict):
                doc.style_tokens = styleTokens
            if themeKey:
                doc.theme_key = themeKey

            await db.commit()
            await db.refresh(doc)
            return DocumentType(
                documentKey=doc.document_key,
                contentMd=doc.content_md,
                styleTokens=doc.style_tokens,
                themeKey=doc.theme_key,
            )

    @strawberry.mutation
    async def upsertHtmlSnippet(
        self,
        documentKey: str,
        rawHtml: str,
        name: Optional[str] = None,
        snippetId: Optional[strawberry.ID] = None,
    ) -> HtmlSnippetType:
        async with SessionLocal() as db:
            res = await db.execute(select(Document).where(Document.document_key == documentKey))
            doc = res.scalar_one_or_none()
            if not doc:
                doc = Document(document_key=documentKey, content_md="")
                db.add(doc)
                await db.commit()
                await db.refresh(doc)

            # sanitize snippet
            from app.sanitize import sanitize_html
            sanitized, warnings = sanitize_html(rawHtml or "")

            snippet = None
            if snippetId:
                res2 = await db.execute(
                    select(HtmlSnippet).where(HtmlSnippet.id == str(snippetId), HtmlSnippet.document_id == doc.id)
                )
                snippet = res2.scalar_one_or_none()

            if not snippet:
                snippet = HtmlSnippet(
                    document_id=doc.id,
                    name=name,
                    raw_html=rawHtml or "",
                    sanitized_html=sanitized,
                    warnings=warnings,
                )
                db.add(snippet)
            else:
                snippet.name = name
                snippet.raw_html = rawHtml or ""
                snippet.sanitized_html = sanitized
                snippet.warnings = warnings

            await db.commit()
            await db.refresh(snippet)

            return HtmlSnippetType(
                id=str(snippet.id),
                name=snippet.name,
                rawHtml=snippet.raw_html,
                sanitizedHtml=snippet.sanitized_html,
                warnings=snippet.warnings,
            )

    @strawberry.mutation
    async def deleteHtmlSnippet(self, documentKey: str, snippetId: strawberry.ID) -> bool:
        async with SessionLocal() as db:
            res = await db.execute(select(Document).where(Document.document_key == documentKey))
            doc = res.scalar_one_or_none()
            if not doc:
                return False
            res2 = await db.execute(
                select(HtmlSnippet).where(HtmlSnippet.id == str(snippetId), HtmlSnippet.document_id == doc.id)
            )
            snippet = res2.scalar_one_or_none()
            if not snippet:
                return False
            await db.delete(snippet)
            await db.commit()
            return True

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

### `services/editor-api/app/main.py` (REPLACE)

Protect `/graphql` with API key dependency.

```python
from fastapi import FastAPI, Depends
from strawberry.fastapi import GraphQLRouter
from app.schema import schema
from app.db import Base, engine
from app.security import require_api_key

app = FastAPI()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(
    GraphQLRouter(schema),
    prefix="/graphql",
    dependencies=[Depends(require_api_key)],
)

@app.get("/health")
async def health():
    return {"ok": True}
```

---

## 2) FRONTEND UPGRADE (web)

### `web/src/api.ts` (REPLACE)

Adds `x-api-key`.

```ts
const GRAPHQL_URL = "http://localhost:8000/graphql";
const API_KEY = "dev-key";

export async function gql(query: string, variables: any = {}) {
  const res = await fetch(GRAPHQL_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": API_KEY,
    },
    body: JSON.stringify({ query, variables }),
  });

  const json = await res.json();
  if (json.errors) throw new Error(json.errors[0].message);
  return json.data;
}
```

### `web/src/snippetToken.ts` (NEW)

```ts
export function makeSnippetToken(id: string) {
  return `[[html_snippet:${id}]]`;
}
```

### `web/src/HtmlSnippetModal.tsx` (NEW)

```tsx
import React from "react";
import { gql } from "./api";

export function HtmlSnippetModal({
  open,
  onClose,
  documentKey,
  onInserted,
}: {
  open: boolean;
  onClose: () => void;
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
      const data = await gql(
        `
        mutation Upsert($documentKey: String!, $rawHtml: String!) {
          upsertHtmlSnippet(documentKey: $documentKey, rawHtml: $rawHtml) {
            id
            warnings
            sanitizedHtml
          }
        }
        `,
        { documentKey, rawHtml }
      );
      setSnippetId(data.upsertHtmlSnippet.id);
      setWarnings(data.upsertHtmlSnippet.warnings);
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
      <div style={{ width: 860, background: "#fff", padding: 16, borderRadius: 12 }}>
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
            Insert Token
          </button>
        </div>

        {warnings ? (
          <pre style={{ marginTop: 10, background: "#f6f8fa", padding: 10, borderRadius: 10, maxHeight: 140, overflow: "auto" }}>
            {JSON.stringify(warnings, null, 2)}
          </pre>
        ) : null}
      </div>
    </div>
  );
}
```

### `web/src/Editor.tsx` (REPLACE)

Crepe initialized after loading markdown; inserts token at cursor using `insert(...)` macro. ([milkdown.dev][1])

```tsx
import React, { useEffect, useRef, useState } from "react";
import { Crepe } from "@milkdown/crepe";
import "@milkdown/crepe/theme/common/style.css";
import "@milkdown/crepe/theme/frame.css";

import { insert } from "@milkdown/kit/utils";
import { gql } from "./api";
import { Preview } from "./Preview";
import { HtmlSnippetModal } from "./HtmlSnippetModal";
import { makeSnippetToken } from "./snippetToken";

export function Editor() {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const crepeRef = useRef<Crepe | null>(null);

  const [html, setHtml] = useState("");
  const [themeCss, setThemeCss] = useState(".editor-content{}");
  const [loading, setLoading] = useState(true);
  const [snippetOpen, setSnippetOpen] = useState(false);

  const documentKey = "siteA:blog:demo";

  const refreshRender = async () => {
    const data = await gql(
      `
      query Render($key: String!) {
        render(documentKey: $key) { contentHtml themeCss }
      }
      `,
      { key: documentKey }
    );
    setHtml(data.render.contentHtml);
    setThemeCss(data.render.themeCss);
  };

  useEffect(() => {
    if (!rootRef.current) return;

    (async () => {
      setLoading(true);

      // Load current markdown
      const data = await gql(
        `
        query Doc($key: String!) {
          document(documentKey: $key) { contentMd }
        }
        `,
        { key: documentKey }
      );

      const md = data.document?.contentMd ?? "# Start writing...\n";

      // Create Crepe using loaded markdown as defaultValue
      const crepe = new Crepe({
        root: rootRef.current!,
        defaultValue: md,
      });

      crepeRef.current = crepe;
      await crepe.create();

      // Autosave on markdown updates
      crepe.on((listener) => {
        listener.markdownUpdated(async (_, markdown) => {
          await gql(
            `
            mutation Save($key: String!, $md: String!) {
              saveDocument(documentKey: $key, contentMd: $md) { documentKey }
            }
            `,
            { key: documentKey, md: markdown }
          );
          await refreshRender();
        });
      });

      await refreshRender();
      setLoading(false);
    })();

    return () => {
      crepeRef.current?.destroy();
      crepeRef.current = null;
    };
  }, []);

  const insertSnippetTokenAtCursor = async (snippetId: string) => {
    const crepe = crepeRef.current;
    if (!crepe) return;

    const token = makeSnippetToken(snippetId);

    // Insert at cursor via Milkdown action macro
    crepe.editor.action(insert("\n\n" + token + "\n\n", false)); // false = block insert
    // No manual save needed: markdownUpdated will fire and persist+render
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
      <div>
        <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
          <button onClick={() => setSnippetOpen(true)} disabled={loading}>Insert HTML Snippet</button>
          <button onClick={refreshRender} disabled={loading}>Refresh Preview</button>
        </div>
        <div ref={rootRef} />
      </div>

      <div>
        <style>{themeCss}</style>
        <Preview html={html} />
      </div>

      <HtmlSnippetModal
        open={snippetOpen}
        onClose={() => setSnippetOpen(false)}
        documentKey={documentKey}
        onInserted={insertSnippetTokenAtCursor}
      />
    </div>
  );
}
```

---

## 3) What to run

1. Start backend + Postgres:

```bash
docker compose up --build
```

2. Start the web app.
3. Click **Insert HTML Snippet** → paste embed (YouTube/Vimeo allowed), validate/save → token inserts at cursor and renders.

---

## 4) What this version now supports

* Render HTML snippets as HTML (sanitized) with iframe allowlist
* Server-side render output + theme CSS variables
* Microservice-ready GraphQL: `document`, `snippets`, `render`, `saveDocument`, `upsertHtmlSnippet`, `deleteHtmlSnippet`

If you say “add style controls”, I’ll send the next files: a small ThemePanel UI that writes `styleTokens` to `saveDocument(...)`, plus a default `.editor-content` stylesheet that uses the CSS vars.

[1]: https://milkdown.dev/docs/api/utils?utm_source=chatgpt.com "Utils"
