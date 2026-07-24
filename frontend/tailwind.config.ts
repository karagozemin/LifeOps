import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#090b0b",
        panel: "#111414",
        surface: "#171b1b",
        edge: "#2b3030",
        muted: "#8b9494",
        accent: "#b8f34a",
        "accent-strong": "#cbff68",
        danger: "#ff5b5b",
        warn: "#f7b955",
        ok: "#52d99a",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
