import React from "react";
import { MilkdownProvider, useEditor } from "@milkdown/react";
import { Editor as MdEditor } from "@milkdown/core";
import { commonmark } from "@milkdown/preset-commonmark";

import { EditorClientConfig } from "../api/client";
import { loadDocument, saveDocument, renderDocument } from "../api/ops";
import { HtmlSnippetModal } from "./HtmlSnippetModal";
import { Preview } from "./Preview";
import { makeSnippetToken } from "../milkdown/snippetSyntax";

function debounce<T extends (...args: any[]) => void>(fn: T, ms: number) {
  let t: any;
  return (...args: Parameters<T>) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

export function Editor({
  cfg,
  documentKey,
}: {
  cfg: EditorClientConfig;
  documentKey: string;
}) {
  const [title, setTitle] = React.useState("");
  const [md, setMd] = React.useState("");
  const [renderedHtml, setRenderedHtml] = React.useState("");
  const [themeCss, setThemeCss] = React.useState(".editor-content{}");
  const [snippetOpen, setSnippetOpen] = React.useState(false);

  // Load doc
  React.useEffect(() => {
    (async () => {
      const doc = await loadDocument(cfg, documentKey);
      if (doc) {
        setTitle(doc.title || "");
        setMd(doc.contentMd || "");
      } else {
        setTitle("");
        setMd("");
      }
      const r = await renderDocument(cfg, documentKey);
      setRenderedHtml(r.contentHtml);
      setThemeCss(r.themeCss);
    })();
  }, [cfg.graphqlUrl, cfg.apiKey, documentKey]);

  // Milkdown editor
  const editor = useEditor((root) => {
    return MdEditor.make()
      .config((ctx) => {
        // Milkdown react sets root internally; keep minimal here
      })
      .use(commonmark)
      .create();
  });

  // Autosave markdown and refresh preview
  const autosave = React.useMemo(
    () =>
      debounce(async (nextMd: string) => {
        await saveDocument(cfg, {
          documentKey,
          title,
          contentMd: nextMd,
          styleTokens: null,
          themeKey: null,
        });
        const r = await renderDocument(cfg, documentKey);
        setRenderedHtml(r.contentHtml);
        setThemeCss(r.themeCss);
      }, 650),
    [cfg.graphqlUrl, cfg.apiKey, documentKey, title]
  );

  const insertSnippetToken = async (snippetId: string) => {
    const token = makeSnippetToken(snippetId);
    const next = (md || "") + "\n\n" + token + "\n";
    setMd(next);
    await saveDocument(cfg, { documentKey, title, contentMd: next, styleTokens: null, themeKey: null });
    const r = await renderDocument(cfg, documentKey);
    setRenderedHtml(r.contentHtml);
    setThemeCss(r.themeCss);
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      <div>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          style={{ width: "100%", padding: 10, fontSize: 16 }}
        />
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <button onClick={() => setSnippetOpen(true)}>Insert HTML Snippet</button>
        </div>

        <div style={{ marginTop: 10, border: "1px solid #ddd", borderRadius: 10, padding: 10, minHeight: 360 }}>
          {/* Simple textarea for md state bridge (Milkdown hookup varies by integration) */}
          <textarea
            value={md}
            onChange={(e) => {
              const next = e.target.value;
              setMd(next);
              autosave(next);
            }}
            style={{ width: "100%", height: 340, fontFamily: "monospace", border: 0, outline: "none" }}
          />
        </div>

        {/* Milkdown UI placeholder (wire later once you decide exact Milkdown React pattern) */}
        <div style={{ marginTop: 10, opacity: 0.7, fontSize: 12 }}>
          Milkdown can replace the textarea once you finalize the editor binding strategy.
        </div>
      </div>

      <div>
        <div style={{ border: "1px solid #ddd", borderRadius: 10, padding: 10, minHeight: 420 }}>
          <Preview html={renderedHtml} themeCss={themeCss} />
        </div>
      </div>

      <HtmlSnippetModal
        open={snippetOpen}
        onClose={() => setSnippetOpen(false)}
        cfg={cfg}
        documentKey={documentKey}
        onInserted={insertSnippetToken}
      />
    </div>
  );
}
