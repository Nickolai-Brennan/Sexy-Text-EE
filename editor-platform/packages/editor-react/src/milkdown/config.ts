// Milkdown editor preset configuration: plugins and keybindings
// Wire up plugins here as needed (commonmark, history, etc.)
import { defaultValueCtx, Editor, rootCtx } from "@milkdown/core";
import { commonmark } from "@milkdown/preset-commonmark";

export function createEditorConfig(root: HTMLElement, initialValue: string) {
  return Editor.make()
    .config((ctx) => {
      ctx.set(rootCtx, root);
      ctx.set(defaultValueCtx, initialValue);
    })
    .use(commonmark);
}
