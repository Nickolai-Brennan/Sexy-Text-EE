import { makeSnippetToken } from "./snippetSyntax";

// Insert a snippet token at the end of current markdown content
export function insertSnippetToken(currentMd: string, snippetId: string): string {
  const token = makeSnippetToken(snippetId);
  return (currentMd || "") + "\n\n" + token + "\n";
}
