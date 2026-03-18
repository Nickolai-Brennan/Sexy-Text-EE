export function Preview({ html }: { html: string }) {
  return (
    <div className="editor-content"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}