import React from "react";
import { EditorClientConfig } from "../api/client";
import { upsertSnippet } from "../api/ops";

export function HtmlSnippetModal({
  open,
  onClose,
  cfg,
  documentKey,
  onInserted,
}: {
  open: boolean;
  onClose: () => void;
  cfg: EditorClientConfig;
  documentKey: string;
  onInserted: (snippetId: string) => void;
}) {
  const [rawHtml, setRawHtml] = React.useState(`<div class="callout">Hello</div>`);
  const [warnings, setWarnings] = React.useState<any>(null);
  const [snippetId, setSnippetId] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  if (!open) return null;

  const validateAndSave = async () => {
    setBusy(true);
    try {
      const res = await upsertSnippet(cfg, { documentKey, rawHtml });
      setSnippetId(res.id);
      setWarnings(res.warnings);
    } finally {
      setBusy(false);
    }
  };

  const insert = () => {
    if (!snippetId) return;
    onInserted(snippetId);
    onClose();
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "grid", placeItems: "center" }}>
      <div style={{ width: 820, background: "#fff", padding: 16, borderRadius: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <strong>Insert HTML Snippet</strong>
          <button onClick={onClose}>X</button>
        </div>

        <textarea
          value={rawHtml}
          onChange={(e) => setRawHtml(e.target.value)}
          style={{ width: "100%", height: 220, marginTop: 10, fontFamily: "monospace" }}
        />

        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
          <button onClick={validateAndSave} disabled={busy}>
            {busy ? "Validating..." : "Validate & Save"}
          </button>
          <button onClick={insert} disabled={!snippetId}>
            Insert Into Document
          </button>
        </div>

        {warnings ? (
          <pre style={{ marginTop: 10, background: "#f6f8fa", padding: 10, borderRadius: 10, maxHeight: 120, overflow: "auto" }}>
            {JSON.stringify(warnings, null, 2)}
          </pre>
        ) : null}
      </div>
    </div>
  );
}
