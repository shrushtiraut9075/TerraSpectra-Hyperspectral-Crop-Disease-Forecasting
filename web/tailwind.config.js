/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        terra: {
          dark: "#0b0f17",
          panel: "#111827",
          border: "#1f293d",
          accent: "#10b981", // Emerald agricultural green
          accentHover: "#059669",
          muted: "#94a3b8",
          highlight: "#38bdf8"
        }
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"]
      }
    },
  },
  plugins: [],
}

