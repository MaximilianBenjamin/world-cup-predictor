/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Legacy tokens — kept so unreskinned pages don't shift.
        ink:    "#0b0f16",
        paper:  "#11171f",
        edge:   "#1c2632",

        // "Pool" palette — deep navy, vivid orange, teal, cream.
        accent: "#f1600d",   // primary / brand / CTA — vivid orange
        amber:  "#f4915a",   // lighter orange for gradients
        pick:   "#50a5b1",   // selected picks + combined odds — teal
        cream:  "#fef6ed",   // light surface / text
        warn:   "#f4915a",
        bad:    "#fb7185",
        muted:  "#8a93b8",   // navy-tinted muted text

        home:   "#50a5b1",   // home-team accent (1X2 viz) — teal
        away:   "#f1600d",   // away-team accent — orange
        dim:    "rgba(254,246,237,0.42)",

        // Glass surfaces layered on the navy gradient background.
        glass:         "rgba(255,255,255,0.05)",
        "glass-strong": "rgba(255,255,255,0.08)",
        "glass-hover": "rgba(255,255,255,0.11)",
        "glass-border": "rgba(255,255,255,0.10)",
        "glass-border-strong": "rgba(255,255,255,0.18)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "SF Pro Display",
          "-apple-system",
          "BlinkMacSystemFont",
          "system-ui",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      backgroundImage: {
        "app-gradient":
          "radial-gradient(ellipse at top, #2a3a7a 0%, #1a265a 55%, #101740 100%)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(100%)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%,100%": { transform: "translate(0,0) scale(1)" },
          "50%": { transform: "translate(2%,-3%) scale(1.05)" },
        },
        pop: {
          "0%": { transform: "scale(0.96)" },
          "60%": { transform: "scale(1.03)" },
          "100%": { transform: "scale(1)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.4s ease-out both",
        "slide-up": "slide-up 0.28s cubic-bezier(0.16,1,0.3,1) both",
        float: "float 18s ease-in-out infinite",
        pop: "pop 0.2s ease-out",
        shimmer: "shimmer 1.6s infinite",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(255,255,255,0.06), 0 18px 50px -12px rgba(0,0,0,0.55)",
        pick: "0 0 24px -6px rgba(80,165,177,0.5)",
      },
    },
  },
  plugins: [],
};
