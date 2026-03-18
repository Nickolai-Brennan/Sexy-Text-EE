import React, { useEffect, useRef, useState } from "react";
import { Crepe } from "@milkdown/crepe";
import "@milkdown/crepe/theme/common/style.css";
import "@milkdown/crepe/theme/frame.css";
import { gql } from "./api";
import { Preview } from "./Preview";

export function Editor() {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [html, setHtml] = useState("");
  const documentKey = "siteA:blog:demo";

  useEffect(() => {
    if (!rootRef.current) return;

    const crepe = new Crepe({
      root: rootRef.current,
      defaultValue: "# Start writing...",
    });

    crepe.create();

    crepe.on((listener) => {
      listener.markdownUpdated(async (_, markdown) => {
        const data = await gql(
          `
          mutation Save($key: String!, $md: String!) {
            saveDocument(documentKey: $key, contentMd: $md) {
              contentHtml
            }
          }
        `,
          { key: documentKey, md: markdown }
        );
        setHtml(data.saveDocument.contentHtml);
      });
    });

    return () => crepe.destroy();
  }, []);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
      <div ref={rootRef}></div>
      <Preview html={html} />
    </div>
  );
}