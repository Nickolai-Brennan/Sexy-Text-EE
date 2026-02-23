import { defaultTokens, ThemeTokens } from "./tokens";

const TOKEN_TO_CSS_VAR: Record<keyof ThemeTokens, string> = {
  fontFamily: "--ed-font-family",
  fontSize: "--ed-font-size",
  lineHeight: "--ed-line-height",
  maxWidth: "--ed-max-width",
  textColor: "--ed-text-color",
  linkColor: "--ed-link-color",
  codeBg: "--ed-code-bg",
  radius: "--ed-radius",
  spacing: "--ed-spacing",
};

export function applyTokens(tokens: Partial<ThemeTokens> = {}): string {
  const merged = { ...defaultTokens, ...tokens };
  const parts = (Object.keys(TOKEN_TO_CSS_VAR) as Array<keyof ThemeTokens>).map(
    (key) => `${TOKEN_TO_CSS_VAR[key]}:${merged[key]}`
  );
  return `.editor-content{${parts.join(";")}}`;
}
