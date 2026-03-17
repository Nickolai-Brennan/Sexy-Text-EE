# Sexy-Text-EE

**Microservice Text Editor Built For Backend and Frontend Applications**

Sexy-Text-EE is a full-stack, microservice-based rich-text editor platform. It pairs a drop-in React editor component with a standalone GraphQL API that stores documents, sanitizes HTML snippets, and returns rendered HTML with scoped theme CSS — ready to embed in any web application.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
  - [React Component](#react-component)
  - [GraphQL API](#graphql-api)
  - [HTML Snippets](#html-snippets)
  - [Theme System](#theme-system)
- [Security](#security)
- [Development](#development)

---

## Overview

Sexy-Text-EE is designed to be dropped into any backend or frontend application as a self-contained editing service. The editor lives in the browser as a Milkdown-powered markdown editor; documents, snippets, and theme data are persisted and rendered server-side by a FastAPI + PostgreSQL microservice exposed over GraphQL.

```
Browser (React) ──GraphQL──► FastAPI API ──SQLAlchemy──► PostgreSQL
     │                            │
  Milkdown editor            Render engine
  HTML preview                (markdown → HTML, snippet injection, theming)
```

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Drop-in React editor** | `<Editor />` component built on Milkdown; just pass a `documentKey` and API config |
| **Markdown + HTML snippets** | Write markdown, embed sanitized raw-HTML blocks via UUID tokens |
| **Server-side rendering** | Markdown → HTML conversion and snippet injection happen on the API |
| **Scoped CSS theming** | Style tokens are compiled to `--ed-*` CSS variables scoped to `.editor-content` |
| **HTML sanitization** | Strict allowlist (Bleach + custom rules) strips dangerous attributes and enforces iframe domain allowlisting |
| **Auto-save** | Debounced (650 ms) save on every keystroke — no manual save required |
| **Framework-agnostic SDK** | `editor-sdk` package exposes raw GraphQL operations for non-React consumers |
| **Docker-first setup** | One `docker compose up --build` starts the full stack |

---

## Architecture

```
editor-platform/
├── packages/
│   ├── editor-react/      # React <Editor /> component (Milkdown, TypeScript)
│   └── editor-sdk/        # Framework-agnostic GraphQL client (TypeScript)
├── services/
│   └── editor-api/        # FastAPI + Strawberry GraphQL + SQLAlchemy (Python)
├── apps/
│   └── playground/        # Local Vite app for testing the editor package
└── infrastructure/
    ├── docker-compose.yml  # Orchestrates API + PostgreSQL
    └── postgres/init.sql   # DB schema bootstrap
```

### Data Flow

1. The React `<Editor />` loads a document by `documentKey` via GraphQL.
2. The user edits markdown; HTML snippet blocks are inserted as `[[html_snippet:<uuid>]]` tokens.
3. Changes are auto-saved (`upsertDocument` / `upsertHtmlSnippet` mutations).
4. The `render` query converts markdown → HTML, injects snippet HTML, applies sanitization, and returns `contentHtml` + `themeCss`.
5. The `<Preview />` component renders the result with DOMPurify client-side guard.

---

## Tech Stack

### Frontend (TypeScript)

| Package | Role |
|---------|------|
| React 18 | UI framework |
| Milkdown 7.7 | Composable markdown editor |
| Vite 5.4 | Build tool |
| DOMPurify 3.0 | Client-side HTML sanitization guard |
| TypeScript 5.5 | Type safety across all packages |

### Backend (Python 3.11+)

| Package | Role |
|---------|------|
| FastAPI 0.110 | Async web framework |
| Strawberry GraphQL 0.235 | GraphQL schema + resolver layer |
| SQLAlchemy 2.0 (async) | ORM |
| asyncpg 0.29 | Async PostgreSQL driver |
| Bleach 6.1 | HTML sanitization |
| markdown-it-py 3.0 | Markdown → HTML conversion |
| BeautifulSoup4 4.12 | HTML parsing utilities |
| Uvicorn 0.27 | ASGI server |

### Infrastructure

| Tool | Role |
|------|------|
| PostgreSQL 15 | Persistent storage |
| Docker & Docker Compose | Containerised local/production deployment |

---

## Project Structure

```
Sexy-Text-EE/
│
├── README.md                         ← You are here
├── Folder Hierarchy + Contracts.md
├── Project To-Do.md
├── starter code files.md
│
└── editor-platform/
    ├── .env.example
    ├── README.md                     ← editor-platform-specific docs
    │
    ├── packages/
    │   ├── editor-react/             # @editor-platform/editor-react
    │   │   └── src/
    │   │       ├── components/       # Editor, Preview, HtmlSnippetModal, Toolbar, ThemePanel
    │   │       ├── api/              # GraphQL client + typed operations
    │   │       ├── milkdown/         # Editor config, commands, snippet syntax
    │   │       └── theming/          # Token definitions + CSS variable helpers
    │   └── editor-sdk/               # @editor-platform/editor-sdk
    │       └── src/                  # Framework-agnostic GraphQL operations
    │
    ├── services/
    │   └── editor-api/               # Python FastAPI service
    │       └── app/
    │           ├── core/             # Config + API key security
    │           ├── db/               # SQLAlchemy session + base
    │           ├── models/           # Document, HtmlSnippet ORM models
    │           ├── graphql/          # Strawberry schema, types, resolvers, context
    │           ├── services/         # Render, snippet, theme, document business logic
    │           └── utils/            # sanitize.py, markdown.py, text.py
    │
    ├── apps/
    │   └── playground/               # Vite + React dev harness
    │
    └── infrastructure/
        ├── docker-compose.yml
        └── postgres/init.sql
```

---

## Prerequisites

- **Docker & Docker Compose** (recommended) — for the full stack
- **Node.js 18+** and **npm 9+** — for frontend packages
- **Python 3.11+** and **pip** — for local backend development

---

## Quick Start

### Option A — Docker (recommended)

```bash
# 1. Clone the repo
git clone https://github.com/Nickolai-Brennan/Sexy-Text-EE.git
cd Sexy-Text-EE/editor-platform

# 2. Copy environment variables
cp .env.example .env

# 3. Start PostgreSQL + API
cd infrastructure
docker compose up --build

# API is now running at http://localhost:8000
# GraphQL playground: http://localhost:8000/graphql
```

### Option B — Local Development

**Backend:**

```bash
cd editor-platform/services/editor-api
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -e .
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/editor
export API_KEY=dev-key
uvicorn app.main:app --reload
```

**Frontend packages:**

```bash
cd editor-platform/packages/editor-react
npm install
npm run build
```

**Playground (interactive dev UI):**

```bash
cd editor-platform/apps/playground
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## Configuration

Copy `editor-platform/.env.example` to `editor-platform/.env` and adjust as needed:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/editor` | Async PostgreSQL connection string |
| `API_KEY` | `dev-key` | API key required in `x-api-key` request header |
| `ALLOWED_IFRAME_HOSTS` | `youtube.com,www.youtube.com,youtu.be,player.vimeo.com` | Comma-separated list of iframe `src` domains that pass sanitization |

---

## Usage

### React Component

Install the editor package and render it in your app:

```tsx
import { Editor } from "@editor-platform/editor-react";

export default function App() {
  return (
    <Editor
      cfg={{
        graphqlUrl: "http://localhost:8000/graphql",
        apiKey: "dev-key",
      }}
      documentKey="siteA:blog:post:demo"
    />
  );
}
```

The `documentKey` is a free-form string (e.g. `tenantId:section:id`) that uniquely identifies a document. The editor auto-creates the document on first load.

### GraphQL API

All operations require the `x-api-key` header.

#### Queries

```graphql
# Load a document
query {
  document(documentKey: "siteA:blog:post:demo") {
    documentKey
    title
    contentMd
    styleTokens
  }
}

# Render markdown + snippets to HTML + CSS
query {
  render(documentKey: "siteA:blog:post:demo") {
    contentHtml
    contentText
    themeCss
    warnings
  }
}

# List all HTML snippets for a document
query {
  snippets(documentKey: "siteA:blog:post:demo") {
    id
    rawHtml
    sanitizedHtml
    warnings
  }
}
```

#### Mutations

```graphql
# Create or update a document
mutation {
  upsertDocument(input: {
    documentKey: "siteA:blog:post:demo"
    title: "My First Post"
    contentMd: "# Hello World\n\nThis is a paragraph."
    styleTokens: "{\"fontFamily\": \"Inter, sans-serif\"}"
  }) {
    documentKey
    title
  }
}

# Create or update an HTML snippet (automatically sanitised)
mutation {
  upsertHtmlSnippet(input: {
    documentKey: "siteA:blog:post:demo"
    rawHtml: "<div class=\"callout\"><p>Important note</p></div>"
  }) {
    id
    sanitizedHtml
    warnings
  }
}

# Delete a snippet
mutation {
  deleteHtmlSnippet(
    documentKey: "siteA:blog:post:demo"
    snippetId: "8f3f7a2c-2d7e-4a8a-a8a1-1f0b0b9a7c3f"
  )
}
```

#### cURL Example

```bash
curl -s http://localhost:8000/graphql \
  -H "content-type: application/json" \
  -H "x-api-key: dev-key" \
  -d '{"query":"{ render(documentKey:\"siteA:blog:post:demo\"){ contentHtml themeCss warnings } }"}' \
  | jq
```

### HTML Snippets

HTML snippets are embedded in markdown using a UUID token:

```
[[html_snippet:8f3f7a2c-2d7e-4a8a-a8a1-1f0b0b9a7c3f]]
```

On render, each token is replaced with its `sanitizedHtml`. Snippets are stored and sanitised separately so the same snippet can be reused in multiple documents.

### Theme System

Style tokens are stored as JSON on the document and compiled to scoped CSS variables at render time:

```json
{
  "fontFamily": "Inter, system-ui, sans-serif",
  "fontSize": "16px",
  "lineHeight": "1.7",
  "maxWidth": "720px",
  "textColor": "#1a1a1a",
  "linkColor": "#0066cc",
  "codeBg": "#f5f5f5",
  "radius": "4px",
  "spacing": "1.5rem"
}
```

The API compiles these to:

```css
.editor-content {
  --ed-font-family: Inter, system-ui, sans-serif;
  --ed-font-size: 16px;
  --ed-line-height: 1.7;
  --ed-max-width: 720px;
  --ed-text-color: #1a1a1a;
  --ed-link-color: #0066cc;
  --ed-code-bg: #f5f5f5;
  --ed-radius: 4px;
  --ed-spacing: 1.5rem;
}
```

---

## Security

The platform applies multiple layers of HTML sanitization to prevent XSS and injection attacks:

- **Allowlist-only tags** — only a curated set of HTML elements is permitted (headings, paragraphs, lists, tables, links, images, iframes, etc.)
- **Event handler stripping** — all `on*` attributes (e.g. `onclick`, `onerror`) are removed
- **Iframe domain allowlisting** — iframes are only allowed from hosts listed in `ALLOWED_IFRAME_HOSTS`; others are removed with a warning
- **Sandbox enforcement** — iframes automatically receive `sandbox="allow-scripts allow-same-origin"` attributes
- **Link safety** — `target="_blank"` links are automatically given `rel="noopener noreferrer"`
- **Client-side guard** — the `<Preview />` component additionally runs rendered HTML through DOMPurify before injecting into the DOM
- **API key auth** — all GraphQL operations require a valid `x-api-key` header

---

## Development

### Adding a New Theme Token

1. Add the key to `editor-platform/packages/editor-react/src/theming/tokens.ts`.
2. Add the CSS variable mapping in `editor-platform/services/editor-api/app/services/theme_service.py`.

### Adding a New GraphQL Operation

1. Define the type in `app/graphql/types.py`.
2. Add the resolver in `app/graphql/resolvers.py`.
3. Add the corresponding operation in `packages/editor-react/src/api/ops.ts` (and `editor-sdk` if needed).

### Running the API Locally with Hot-Reload

```bash
cd editor-platform/services/editor-api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Building the React Package

```bash
cd editor-platform/packages/editor-react
npm run build
# Output: dist/index.js, dist/index.d.ts
```
