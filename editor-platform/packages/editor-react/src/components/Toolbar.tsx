import React from "react";

export type ToolbarAction = "bold" | "italic" | "code" | "snippet";

export function Toolbar({ onAction }: { onAction: (action: ToolbarAction) => void }) {
  return (
    <div style={{ display: "flex", gap: 8, padding: "4px 0" }}>
      <button onClick={() => onAction("bold")}><strong>B</strong></button>
      <button onClick={() => onAction("italic")}><em>I</em></button>
      <button onClick={() => onAction("code")}>{"<>"}</button>
      <button onClick={() => onAction("snippet")}>HTML Snippet</button>
    </div>
  );
}
