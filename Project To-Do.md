## Step-by-step build plan: Editor Microservice (FastAPI + GraphQL + Postgres) + React Milkdown Editor

Goal: one reusable editor you can embed into multiple sites, with rendered HTML snippets + adjustable CSS via style tokens.

### Phase 0: Prereqs

1. Install tooling

* Node 18+ (or 20+)
* Python 3.11+
* Postgres 14+

2. Pick workspace manager

* pnpm (recommended) or yarn/npm

3. Decide your local dev ports (example)

* Postgres: 5432
* editor-api: 8000
* playground web: 5173

---

## Phase 1: Create repo skeleton

1. Create folders

* `editor-platform/`
* `packages/editor-react/`
* `services/editor-api/`
* `apps/playground/`
* `infrastructure/`

2. Add root workspace config

* `package.json` (workspaces)
* `pnpm-workspace.yaml` (or turbo)

3. Add `docker-compose.yml` for local dev (Postgres + api)

Deliverable at end of Phase 1: repo boots with Postgres container.

---

## Phase 2: Build the Editor API microservice (FastAPI + GraphQL)

### 2.1 Initialize FastAPI service

1. In `services/editor-api/`

* create `pyproject.toml` (poetry/uv/pip-tools—your choice)

2. Install dependencies

* fastapi
* uvicorn
* strawberry-graphql[fastapi]
* sqlalchemy + asyncpg (or psycopg)
* alembic
* markdown rendering library (choose one: markdown-it-py or mistune)
* html sanitizer (Python: bleach)
* html-to-text (optional) or use BeautifulSoup

Deliverable: `GET /health` and `POST /graphql` running.

### 2.2 Create database layer

1. Add `app/db/session.py`

* engine + sessionmaker

2. Add Alembic

* `alembic init app/db/migrations`

3. Create migrations for:

* `documents`
* `document_html_snippets`

Deliverable: `alembic upgrade head` creates tables.

### 2.3 Implement sanitizer policy (render-as-HTML snippets)

1. Create `app/utils/sanitize.py`

* allowlist tags/attrs
* iframe domain allowlist (youtube/vimeo)
* strip `on*` handlers
* enforce `rel` on external links

2. Build snippet validator

* input raw HTML → output sanitized HTML + warnings list

Deliverable: unit test: unsafe `<script>` removed; unsafe iframe rejected.

### 2.4 Implement GraphQL schema + resolvers

1. Add `app/graphql/schema.py`
2. Add types:

* Document
* HtmlSnippet
* RenderResult

3. Add resolvers:

* Query: `document(documentKey)`
* Query: `snippets(documentKey)`
* Query: `render(documentKey)`
* Mutation: `upsertDocument(input)`
* Mutation: `upsertHtmlSnippet(input)`
* Mutation: `deleteHtmlSnippet(documentKey, snippetId)`

Deliverable: GraphQL operations work via GraphiQL.

### 2.5 Implement render pipeline

1. Render steps for `render(documentKey)`

* Load document markdown
* Replace tokens `[[html_snippet:UUID]]` with snippet `sanitized_html`
* Convert markdown → HTML
* Sanitize final HTML (second-pass safety)
* Convert HTML → plain text (content_text)
* Compile theme tokens → scoped CSS vars string (`themeCss`)

2. Return: `{contentHtml, contentText, themeCss, warnings}`

Deliverable: render returns production-grade output.

---

## Phase 3: React editor package (Milkdown)

### 3.1 Create `packages/editor-react`

1. Initialize package

* TypeScript + Vite library mode (or tsup)

2. Install dependencies

* Milkdown core/react preset(s)
* DOMPurify (for safe preview render)
* small modal UI (or your existing UI kit)

Deliverable: build outputs ESM package.

### 3.2 Implement Editor component

1. `Editor.tsx` props

* `baseUrl`
* `documentKey`
* `authToken` (string or function)
* `initialThemeTokens` (optional)
* `onSaved`, `onError`

2. Features in component

* load doc on mount
* edit markdown in Milkdown
* autosave (debounced)
* Preview pane using `render(documentKey)` from API

Deliverable: editing updates markdown and preview updates via API render.

### 3.3 Implement HTML Snippet Modal

1. Add “Insert HTML Snippet” button
2. Modal fields

* name (optional)
* raw HTML textarea
* Validate button: calls `upsertHtmlSnippet`
* show sanitized preview + warnings

3. Insert token into markdown at cursor:

* `[[html_snippet:<id>]]`

Deliverable: snippet renders as HTML in preview.

### 3.4 Implement Theme panel (CSS adjustability)

1. Build token editor UI (sliders/inputs)

* fontFamily, fontSize, lineHeight, maxWidth, text/link colors, code bg, radius, spacing

2. Save tokens by calling `upsertDocument(styleTokens=...)`
3. Apply returned `themeCss` to preview container

Deliverable: styles change without modifying content.

---

## Phase 4: Playground app (proves embed works)

1. Create `apps/playground` React app
2. Install local package: `editor-react`
3. Configure:

* `baseUrl=http://localhost:8000/graphql`
* `documentKey=siteA:blog:post:demo`

4. Run:

* api + db + playground

Deliverable: one command starts everything and you can author posts.

---

## Phase 5: Integrate into “other sites”

For each site:

1. Install `@your-scope/editor-react`
2. Set a stable documentKey convention

* `siteId:blog:post:<postId>`

3. Provide auth to the editor-api

* API key header OR verify the site’s JWT

4. Render content

* Pull from editor-api `render(documentKey)` OR store/replicate content_html in the site DB

Deliverable: multiple sites share one editor system.

---

# Concrete commands (typical dev loop)

1. Start Postgres + API

* `docker compose up -d postgres`
* `cd services/editor-api && uvicorn app.main:app --reload --port 8000`

2. Start playground

* `cd apps/playground && pnpm dev`

---

## Acceptance checklist (done = usable)

* Create doc by saving markdown
* Insert HTML snippet → sanitizer strips unsafe content
* Snippet token renders as HTML in preview
* Theme tokens adjust typography/colors/layout via scoped CSS vars
* API returns final HTML + text + CSS
* Editor package drops into any React app with `baseUrl` + `documentKey`

If you want, I can turn this into a build checklist with exact file names + “copy/paste” starter code for each step in the order above.
