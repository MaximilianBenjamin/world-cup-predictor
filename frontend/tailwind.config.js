/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0a0a0b",       // page
        coal: "#131315",      // panels
        slab: "#1b1b1e",      // raised rows, inputs
        line: "#2c2c31",      // rules
        red: { DEFAULT: "#d81f2a", deep: "#9b111a", hot: "#ff3b45" },
        chalk: "#f3efe6",     // text
        dust: "#9b978d",      // secondary text
        gold: "#f5c518",      // the model's pick, anything selected
        pitch: "#0f5a2c",
      },
      fontFamily: {
        display: ["Anton", "Impact", "Haettenschweiler", "Arial Narrow Bold", "sans-serif"],
        cond: ["Barlow Condensed", "Arial Narrow", "sans-serif"],
        sans: ["Barlow", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        marquee: { from: { transform: "translateX(0)" }, to: { transform: "translateX(-50%)" } },
      },
      animation: {
        rise: "rise 0.35s cubic-bezier(0.16,1,0.3,1) both",
        marquee: "marquee 110s linear infinite",
      },
    },
  },
  plugins: [],
};
