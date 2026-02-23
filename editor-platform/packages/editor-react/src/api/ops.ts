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
