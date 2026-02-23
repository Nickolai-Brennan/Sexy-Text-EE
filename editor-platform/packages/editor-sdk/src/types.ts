export type DocumentDTO = {
  documentKey: string;
  title?: string | null;
  contentMd: string;
  contentHtml: string;
  contentText: string;
  styleTokens: Record<string, any>;
  themeKey: string;
  createdAt: string;
  updatedAt: string;
};

export type HtmlSnippetDTO = {
  id: string;
  documentId: string;
  name?: string | null;
  rawHtml: string;
  sanitizedHtml: string;
  warnings: any[];
  createdAt: string;
  updatedAt: string;
};

export type RenderResult = {
  contentHtml: string;
  contentText: string;
  themeCss: string;
  warnings: any[];
};

export type UpsertDocumentInput = {
  documentKey: string;
  title?: string | null;
  contentMd: string;
  styleTokens?: Record<string, any> | null;
  themeKey?: string | null;
};

export type UpsertHtmlSnippetInput = {
  documentKey: string;
  snippetId?: string | null;
  name?: string | null;
  rawHtml: string;
};
