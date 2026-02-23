# editor-platform

A monorepo containing a reusable React rich-text editor (Milkdown) and a FastAPI + Strawberry GraphQL microservice for storing documents, sanitizing HTML snippets, and outputting rendered HTML with scoped theme CSS variables.

## Structure

```
editor-platform/
├── packages/
│   ├── editor-react/     # Drop-in React editor (Milkdown)
│   └── editor-sdk/       # Framework-agnostic GraphQL client
├── services/
│   └── editor-api/       # FastAPI + Strawberry GraphQL + Postgres
├── apps/
│   └── playground/       # Local dev UI to test the package
├── infrastructure/
│   ├── docker-compose.yml
│   └── postgres/init.sql
├── .env.example
└── README.md
```

## Quick Start

### 1. Start the API and database

```bash
cd infrastructure
docker compose up --build
```

### 2. Test GraphQL (curl)

```bash
curl -s http://localhost:8000/graphql \
  -H "content-type: application/json" \
  -H "x-api-key: dev-key" \
  -d '{"query":"{ render(documentKey:\"siteA:blog:post:demo\"){ contentHtml themeCss warnings } }"}' | jq
```

### 3. Use in a React app

```tsx
import { Editor } from "@editor-platform/editor-react";

<Editor
  cfg={{ graphqlUrl: "http://localhost:8000/graphql", apiKey: "dev-key" }}
  documentKey="siteA:blog:post:demo"
/>
```

## GraphQL Schema

### Types

- **Document** — stores `contentMd`, `styleTokens`, metadata
- **HtmlSnippet** — stores raw and sanitized HTML snippets
- **RenderResult** — `contentHtml`, `contentText`, `themeCss`, `warnings`

### Key Operations

| Operation | Description |
|-----------|-------------|
| `query document(documentKey)` | Load a document |
| `query render(documentKey)` | Render markdown + snippets → HTML + CSS |
| `query snippets(documentKey)` | List all snippets for a document |
| `mutation upsertDocument(input)` | Create or update a document |
| `mutation upsertHtmlSnippet(input)` | Create or update a sanitized HTML snippet |
| `mutation deleteHtmlSnippet(documentKey, snippetId)` | Delete a snippet |

## Snippet Token Format

Snippets are referenced in markdown using:

```
[[html_snippet:8f3f7a2c-2d7e-4a8a-a8a1-1f0b0b9a7c3f]]
```

On render, the service replaces each token with the snippet's `sanitizedHtml`.

## Theme Tokens

Style tokens are stored as JSON and compiled to scoped CSS variables:

```css
.editor-content {
  --ed-font-family: Inter, system-ui, sans-serif;
  --ed-font-size: 16px;
  /* ... */
}
```
