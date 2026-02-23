import React from "react";
import DOMPurify from "dompurify";

export function Preview({ html, themeCss }: { html: string; themeCss: string }) {
  const safe = React.useMemo(() => DOMPurify.sanitize(html || ""), [html]);

  return (
    <div>
      <style>{themeCss}</style>
      <div className="editor-content" dangerouslySetInnerHTML={{ __html: safe }} />
    </div>
  );
}
