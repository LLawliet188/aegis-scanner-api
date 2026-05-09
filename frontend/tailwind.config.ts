import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#020617",
        accent: "#00D9FF",
        interactive: "#3B82F6",
        primary: "#F0F4F8",
        secondary: "#94A3B8",
        muted: "#475569",
      },
      fontFamily: {
        display: ["Syne", "sans-serif"],
        body: ["DM Sans", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        cyan: "0 0 28px rgba(0, 217, 255, 0.22)",
        "cyan-sm": "0 0 16px rgba(0, 217, 255, 0.18)",
      },
      backgroundImage: {
        "cta-gradient":
          "linear-gradient(135deg, rgba(0,217,255,0.95), rgba(59,130,246,0.82))",
        "heading-gradient":
          "linear-gradient(135deg, #F0F4F8 8%, #BFEFFF 42%, #00D9FF 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
