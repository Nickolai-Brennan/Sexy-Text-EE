import { gql, EditorSDKConfig } from "./client";
import {
  DocumentDTO,
  HtmlSnippetDTO,
  RenderResult,
  UpsertDocumentInput,
  UpsertHtmlSnippetInput,
} from "./types";

const Q_DOCUMENT = `
  query Doc($documentKey: String!) {
    document(documentKey: $documentKey) {
      documentKey title contentMd contentHtml contentText styleTokens themeKey createdAt updatedAt
    }
  }
`;

const M_UPSERT_DOCUMENT = `
  mutation Save($input: UpsertDocumentInput!) {
    upsertDocument(input: $input) {
      documentKey title contentMd styleTokens themeKey updatedAt
    }
  }
`;

const Q_RENDER = `
  query Render($documentKey: String!) {
    render(documentKey: $documentKey) {
      contentHtml contentText themeCss warnings
    }
  }
`;

const M_UPSERT_SNIPPET = `
  mutation UpsertSnippet($input: UpsertHtmlSnippetInput!) {
    upsertHtmlSnippet(input: $input) {
      id name rawHtml sanitizedHtml warnings createdAt updatedAt
    }
  }
`;

const M_DELETE_SNIPPET = `
  mutation DeleteSnippet($documentKey: String!, $snippetId: ID!) {
    deleteHtmlSnippet(documentKey: $documentKey, snippetId: $snippetId)
  }
`;

const Q_SNIPPETS = `
  query Snippets($documentKey: String!) {
    snippets(documentKey: $documentKey) {
      id name rawHtml sanitizedHtml warnings createdAt updatedAt
    }
  }
`;

export async function loadDocument(cfg: EditorSDKConfig, documentKey: string): Promise<DocumentDTO | null> {
  const data = await gql<{ document: DocumentDTO | null }>(cfg, Q_DOCUMENT, { documentKey });
  return data.document;
}

export async function saveDocument(cfg: EditorSDKConfig, input: UpsertDocumentInput): Promise<DocumentDTO> {
  const data = await gql<{ upsertDocument: DocumentDTO }>(cfg, M_UPSERT_DOCUMENT, { input });
  return data.upsertDocument;
}

export async function renderDocument(cfg: EditorSDKConfig, documentKey: string): Promise<RenderResult> {
  const data = await gql<{ render: RenderResult }>(cfg, Q_RENDER, { documentKey });
  return data.render;
}

export async function upsertSnippet(cfg: EditorSDKConfig, input: UpsertHtmlSnippetInput): Promise<HtmlSnippetDTO> {
  const data = await gql<{ upsertHtmlSnippet: HtmlSnippetDTO }>(cfg, M_UPSERT_SNIPPET, { input });
  return data.upsertHtmlSnippet;
}

export async function deleteSnippet(cfg: EditorSDKConfig, documentKey: string, snippetId: string): Promise<boolean> {
  const data = await gql<{ deleteHtmlSnippet: boolean }>(cfg, M_DELETE_SNIPPET, { documentKey, snippetId });
  return data.deleteHtmlSnippet;
}

export async function listSnippets(cfg: EditorSDKConfig, documentKey: string): Promise<HtmlSnippetDTO[]> {
  const data = await gql<{ snippets: HtmlSnippetDTO[] }>(cfg, Q_SNIPPETS, { documentKey });
  return data.snippets;
}
