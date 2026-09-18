import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        "mission-dark": "#0a0e17",
        "mission-panel": "#111827",
        "mission-border": "#1e293b",
        "mission-accent": "#3b82f6",
        "mission-success": "#22c55e",
        "mission-warning": "#f59e0b",
        "mission-danger": "#ef4444",
        "mission-critical": "#dc2626",
        "mission-cyan": "#06b6d4",
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', '"SF Mono"', '"Cascadia Code"', "monospace"],
      },
      animation: {
        "led-pulse": "led-blink 2s ease-in-out infinite",
        "scan": "scan 8s linear infinite",
      },
      keyframes: {
        "led-blink": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
