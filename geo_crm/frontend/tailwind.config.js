/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
        display: [
          "Cal Sans",
          "Inter",
          "ui-sans-serif",
          "system-ui",
        ],
      },
      colors: {
        surface: { DEFAULT: "rgb(8 9 12)", elevated: "rgb(16 18 24)" },
        border: { subtle: "rgb(32 35 45)", DEFAULT: "rgb(45 48 60)" },
        accent: { DEFAULT: "rgb(99 102 241)", dim: "rgb(79 70 229 / 0.2)" },
        brand: { DEFAULT: "rgb(34 197 94)", muted: "rgb(20 83 45)" },
        danger: { DEFAULT: "rgb(239 68 68)" },
      },
      boxShadow: {
        card: "0 0 0 1px rgb(45 48 60 / 0.6), 0 4px 24px rgb(0 0 0 / 0.4)",
        glow: "0 0 40px -10px rgb(99 102 241 / 0.35)",
      },
    },
  },
  plugins: [],
};
