/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        solar: {
          50: "#FFF8E1",
          100: "#FFECB3",
          200: "#FFE082",
          300: "#FFD54F",
          400: "#FFCA28",
          500: "#FFC107",
          600: "#FFB300",
          700: "#FFA000",
          800: "#FF8F00",
          900: "#FF6F00",
        },
        surface: {
          roof: "#FFB300",
          facade: "#42A5F5",
          ground: "#78909C",
        },
        suitability: {
          excellent: "#4CAF50",
          high: "#66BB6A",
          moderate: "#FFC107",
          low: "#FF9800",
          poor: "#F44336",
        },
        dark: {
          50: "#E8EAED",
          100: "#BDC1C6",
          200: "#9AA0A6",
          300: "#80868B",
          400: "#5F6368",
          500: "#3C4043",
          600: "#2D2E31",
          700: "#1E1F22",
          800: "#17181A",
          900: "#0E0F11",
          950: "#0A0B0D",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
