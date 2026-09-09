/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        vh: {
          bg: "#0e1116",
          panel: "#161a22",
          border: "#262c38",
          accent: "#e5b25d",
          accent2: "#7c9c5b",
          danger: "#d96b6b",
          muted: "#8a93a4",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
