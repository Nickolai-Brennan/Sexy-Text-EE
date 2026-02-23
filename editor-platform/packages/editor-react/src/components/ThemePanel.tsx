import React from "react";
import { defaultTokens, ThemeTokens } from "../theming/tokens";

export function ThemePanel({
  tokens,
  onChange,
}: {
  tokens: Partial<ThemeTokens>;
  onChange: (tokens: Partial<ThemeTokens>) => void;
}) {
  const merged = { ...defaultTokens, ...tokens };

  const handleChange = (key: keyof ThemeTokens, value: string) => {
    onChange({ ...tokens, [key]: value });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {(Object.keys(defaultTokens) as Array<keyof ThemeTokens>).map((key) => (
        <label key={key} style={{ display: "flex", flexDirection: "column", fontSize: 13 }}>
          <span style={{ fontWeight: 600 }}>{key}</span>
          <input
            value={merged[key]}
            onChange={(e) => handleChange(key, e.target.value)}
            style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid #ccc" }}
          />
        </label>
      ))}
    </div>
  );
}
