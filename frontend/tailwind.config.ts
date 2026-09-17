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
      },
    },
  },
  plugins: [],
};
export default config;
