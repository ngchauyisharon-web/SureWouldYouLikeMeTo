import type { Types } from "phaser";

/** Cutout palette — ported from legacy Streamlit app.py */
export const theme = {
  primary: "#cb0319",
  primarySoft: "#e4253a",
  secondary: "#006c95",
  tertiary: "#4c6f00",
  surface: "#fffbff",
  surfaceLow: "#fff9e5",
  surfaceHigh: "#f5eb90",
  outline: "#c3bb7a",
  onSurface: "#3d3904",
  fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif",
} as const;

export function phaserTextStyle(size: number): Types.GameObjects.Text.TextStyle {
  return {
    fontFamily: theme.fontFamily,
    fontSize: `${size}px`,
    color: theme.onSurface,
    fontStyle: "800",
  };
}
