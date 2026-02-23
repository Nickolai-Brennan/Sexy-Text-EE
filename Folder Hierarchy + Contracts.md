## Editor Microservice + React Editor Package (Milkdown) Folder Hierarchy + Contracts

This is the “just the editor” platform: a reusable React editor + a FastAPI GraphQL microservice that stores documents, sanitizes HTML snippets, and outputs final renderable HTML with theme CSS variables.

# 1) Monorepo folder hierarchy

```text
/editor-platform
├── packages
│   ├── editor-react/                         # Drop-in React editor (Milkdown)
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── Editor.tsx                # main component
│   │   │   │   ├── Toolbar.tsx
│   │   │   │   ├── HtmlSnippetModal.tsx      # add/edit snippets + validate + preview
│   │   │   │   ├── ThemePanel.tsx            # style token controls
│   │   │   │   └── Preview.tsx               # renders returned HTML
│   │   │   ├── milkdown/
│   │   │   │   ├── config.ts                 # presets/plugins + keybinds
│   │   │   │   ├── commands.ts               # insertSnippetToken(), etc.
│   │   │   │   └── snippetSyntax.ts          # token rules [[html_snippet:uuid]]
│   │   │   ├── theming/
│   │   │   │   ├── tokens.ts                 # token schema + defaults
│   │   │   │   ├── applyTokens.ts            # tokens -> style object/CSS vars
│   │   │   │   └── editor-content.css        # base styling using CSS vars
│   │   │   ├── api/
│   │   │   │   ├── client.ts                 # GraphQL client wrapper
│   │   │   │   ├── ops.ts                    # load/save/render/snippet ops
│   │   │   │   └── types.ts
│   │   │   └── index.ts
│   │   └── package.json
│   │
│   └── editor-sdk/                           # Framework-agnostic client (optional)
│       ├── src/
│       │   ├── client.ts
│       │   ├── ops.ts
│       │   ├── types.ts
│       │   └── index.ts
│       └── package.json
│
├── services
│   └── editor-api/                           # FastAPI + Strawberry GraphQL + Postgres
│       ├── app/
│       │   ├── main.py
│       │   ├── core/
│       │   │   ├── config.py                 # env settings
│       │   │   └── security.py               # API key/JWT verification (thin)
│       │   ├── db/
│       │   │   ├── session.py                # SQLAlchemy engine/session
│       │   │   └── migrations/               # Alembic
│       │   ├── models/
│       │   │   ├── document.py
│       │   │   └── snippet.py
│       │   ├── graphql/
│       │   │   ├── schema.py                 # Strawberry schema root
│       │   │   ├── context.py
│       │   │   ├── types.py                  # GraphQL types
│       │   │   └── resolvers.py              # Query/Mutation resolvers
│       │   ├── services/
│       │   │   ├── render_service.py         # md -> html + snippet injection
│       │   │   ├── snippet_service.py        # sanitize + iframe rules
│       │   │   └── theme_service.py          # tokens -> CSS vars
│       │   └── utils/
│       │       ├── sanitize.py               # allowlist sanitizer policy
│       │       ├── markdown.py               # markdown renderer
│       │       └── text.py                   # html -> text
│       ├── pyproject.toml
│       └── Dockerfile
│
├── apps
│   └── playground/                           # local dev UI to test the package
│       ├── src/
│       └── package.json
│
├── infrastructure
│   ├── docker-compose.yml                    # postgres + editor-api + playground
│   └── postgres/
│       └── init.sql
│
├── .env.example
└── README.md
```

# 2) Postgres tables (microservice)

Use a generic “document” so multiple sites can use the same service.

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_key text UNIQUE NOT NULL,                -- e.g. siteA:blog:post:123
  title text,
  content_md text NOT NULL DEFAULT '',
  content_html text NOT NULL DEFAULT '',
  content_text text NOT NULL DEFAULT '',
  style_tokens jsonb NOT NULL DEFAULT '{}'::jsonb,
  theme_key text NOT NULL DEFAULT 'default',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE document_html_snippets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  name text,
  raw_html text NOT NULL,
  sanitized_html text NOT NULL,
  warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX document_html_snippets_document_id_idx ON document_html_snippets(document_id);
```

# 3) Canonical content + snippet token format

Canonical: `content_md` (Milkdown-friendly)
Snippets: token in markdown:

```md
[[html_snippet:8f3f7a2c-2d7e-4a8a-a8a1-1f0b0b9a7c3f]]
```

On render, the service replaces each token with the snippet’s `sanitized_html`.

# 4) GraphQL schema (contract)

This is the minimum you need to integrate editor into any site.

```graphql
scalar JSON
scalar DateTime

type Document {
  id: ID!
  documentKey: String!
  title: String
  contentMd: String!
  contentHtml: String!
  contentText: String!
  styleTokens: JSON!
  themeKey: String!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type HtmlSnippet {
  id: ID!
  documentId: ID!
  name: String
  rawHtml: String!
  sanitizedHtml: String!
  warnings: JSON!
  createdAt: DateTime!
  updatedAt: DateTime!
}

input UpsertDocumentInput {
  documentKey: String!
  title: String
  contentMd: String!
  styleTokens: JSON
  themeKey: String
}

input UpsertHtmlSnippetInput {
  documentKey: String!
  snippetId: ID
  name: String
  rawHtml: String!
}

type RenderResult {
  contentHtml: String!
  contentText: String!
  themeCss: String!         # scoped CSS vars for .editor-content
  warnings: JSON!           # render warnings (missing snippets, etc.)
}

type Query {
  document(documentKey: String!): Document
  snippets(documentKey: String!): [HtmlSnippet!]!
  render(documentKey: String!): RenderResult!
}

type Mutation {
  upsertDocument(input: UpsertDocumentInput!): Document!
  upsertHtmlSnippet(input: UpsertHtmlSnippetInput!): HtmlSnippet!
  deleteHtmlSnippet(documentKey: String!, snippetId: ID!): Boolean!
}
```

# 5) FastAPI + Strawberry wiring (minimal)

## app/main.py

```python
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from app.graphql.schema import schema

app = FastAPI(title="editor-api")

graphql_app = GraphQLRouter(schema, path="/graphql")
app.include_router(graphql_app, prefix="")
```

## app/graphql/schema.py

```python
import strawberry
from app.graphql.resolvers import Query, Mutation

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

## app/graphql/resolvers.py (structure)

```python
import strawberry
from app.graphql.types import DocumentType, HtmlSnippetType, RenderResultType
from app.services.render_service import render_document
from app.services.snippet_service import upsert_snippet, list_snippets, delete_snippet
from app.services.document_service import upsert_document, get_document

@strawberry.type
class Query:
    @strawberry.field
    def document(self, documentKey: str) -> DocumentType | None:
        return get_document(documentKey)

    @strawberry.field
    def snippets(self, documentKey: str) -> list[HtmlSnippetType]:
        return list_snippets(documentKey)

    @strawberry.field
    def render(self, documentKey: str) -> RenderResultType:
        return render_document(documentKey)

@strawberry.type
class Mutation:
    @strawberry.mutation
    def upsertDocument(self, input) -> DocumentType:
        return upsert_document(input)

    @strawberry.mutation
    def upsertHtmlSnippet(self, input) -> HtmlSnippetType:
        return upsert_snippet(input)

    @strawberry.mutation
    def deleteHtmlSnippet(self, documentKey: str, snippetId: str) -> bool:
        return delete_snippet(documentKey, snippetId)
```

# 6) Sanitizer policy for “render as HTML”

Start strict. Expand only when you need it.

## Allowed tags

* Text/layout: `div span p br hr blockquote`
* Headings: `h1 h2 h3 h4 h5 h6`
* Inline: `strong em u s code`
* Lists: `ul ol li`
* Code: `pre code`
* Links: `a`
* Images: `img figure figcaption`
* Tables: `table thead tbody tr th td`
* Embeds (restricted): `iframe` (only allowlisted domains)

## Allowed attributes

* Global: `class id title aria-* data-*`
* Links: `href target rel`
* Images: `src alt width height loading`
* Iframes: `src width height allow allowfullscreen frameborder` (+ forced `sandbox`)

## Forced rules

* Strip ALL `on*` event handlers
* Strip `<script>`, `<style>`, `<object>`, `<embed>`, `<form>`, etc.
* Normalize links:

  * if `target="_blank"` then enforce `rel="noopener noreferrer"`
* Iframes:

  * allow only if `src` host in allowlist
  * enforce `sandbox="allow-scripts allow-same-origin allow-popups"` (tune later)
  * enforce `referrerpolicy="no-referrer"` (optional)

Initial iframe allowlist:

* `youtube.com`, `www.youtube.com`, `youtu.be`, `player.vimeo.com`

# 7) Theme tokens → scoped CSS vars

Store `style_tokens` as JSON. Return a compiled CSS string scoped to `.editor-content`.

## Token defaults (example)

```ts
export const defaultTokens = {
  fontFamily: "Inter, system-ui, sans-serif",
  fontSize: "16px",
  lineHeight: "1.7",
  maxWidth: "760px",
  textColor: "#111111",
  linkColor: "#0b66ff",
  codeBg: "#f6f8fa",
  radius: "10px",
  spacing: "1rem"
};
```

## Compiler behavior

* Only accept known keys (drop everything else)
* Emit:

```css
.editor-content{--ed-font-family:...;--ed-font-size:...}
```

Then your shared stylesheet uses vars:

```css
.editor-content{
  font-family: var(--ed-font-family);
  font-size: var(--ed-font-size);
  line-height: var(--ed-line-height);
  color: var(--ed-text-color);
  max-width: var(--ed-max-width);
}
.editor-content a{color:var(--ed-link-color)}
.editor-content pre{background:var(--ed-code-bg);border-radius:var(--ed-radius);padding:var(--ed-spacing)}
```

# 8) React editor package integration points

Your reusable component API should look like this (stable across sites):

* `documentKey` (string)
* `baseUrl` (microservice URL)
* `auth` (token or function)
* `themeKey` + `styleTokens`
* callbacks: `onSaved`, `onError`

Editor flow:

1. `loadDocument(documentKey)` → fills title + markdown + tokens
2. Insert/edit snippet → `upsertHtmlSnippet` returns sanitized HTML + warnings
3. Save → `upsertDocument`
4. Preview → `render(documentKey)` returns final HTML + themeCss (matches production)

# 9) What to build first (MVP order)

* editor-api: `upsertDocument`, `document`, `render`
* editor-api: `upsertHtmlSnippet` with sanitizer + iframe allowlist
* editor-react: Milkdown editor + snippet modal + preview panel (uses render)
* theming: token panel + apply returned themeCss to `.editor-content`

