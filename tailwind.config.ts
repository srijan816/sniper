import type { Config } from "tailwindcss";
import defaultTheme from "tailwindcss/defaultTheme";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        sniper: {
          green: "#10D94B",
          "green-hover": "#0DB840",
          "green-muted": "rgba(16, 217, 75, 0.12)",
          charcoal: "#1A1C24",
          "charcoal-light": "#2A2D38",
          pearl: "#F8F9FA",
          ash: "#8E95A3",
          surface: "#FFFFFF",
        },
        status: {
          discovered: { bg: "#F1F3F5", text: "#6B7280" },
          pending: { bg: "#FFF3CD", text: "#856404" },
          approved: { bg: "#D4EDDA", text: "#155724" },
          submitted: { bg: "#CCE5FF", text: "#004085" },
          removed: { bg: "#10D94B", text: "#FFFFFF" },
          failed: { bg: "#F8D7DA", text: "#721C24" },
          whitelisted: { bg: "#8E95A3", text: "#FFFFFF" },
        },
      },
      fontFamily: {
        heading: ["var(--font-heading)", ...defaultTheme.fontFamily.sans],
        body: ["var(--font-body)", ...defaultTheme.fontFamily.sans],
        mono: ["var(--font-mono)", ...defaultTheme.fontFamily.mono],
      },
      fontSize: {
        "app-xs": ["0.75rem", { lineHeight: "1rem" }],
        "app-sm": ["0.8125rem", { lineHeight: "1.25rem" }],
        "app-base": ["0.875rem", { lineHeight: "1.5rem" }],
        "app-lg": ["1rem", { lineHeight: "1.5rem" }],
        "app-xl": ["1.125rem", { lineHeight: "1.75rem" }],
        "app-2xl": ["1.5rem", { lineHeight: "2rem" }],
        "app-3xl": ["1.875rem", { lineHeight: "2.25rem" }],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        "sniper-sm": "0 1px 2px 0 rgba(26, 28, 36, 0.05)",
        "sniper-md": "0 1px 3px 0 rgba(26, 28, 36, 0.08), 0 1px 2px -1px rgba(26, 28, 36, 0.08)",
        "sniper-lg": "0 4px 6px -1px rgba(26, 28, 36, 0.08), 0 2px 4px -2px rgba(26, 28, 36, 0.05)",
        "sniper-focus": "0 0 0 3px rgba(16, 217, 75, 0.25)",
      },
      spacing: {
        "app-gutter": "1.5rem",
        "app-section": "2rem",
        "sidebar-w": "16rem",
        "sidebar-w-collapsed": "4rem",
      },
      keyframes: {
        "pulse-green": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(16, 217, 75, 0.4)" },
          "50%": { boxShadow: "0 0 0 8px rgba(16, 217, 75, 0)" },
        },
        "slide-in-right": {
          "0%": { transform: "translateX(100%)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
      animation: {
        "pulse-green": "pulse-green 2s ease-in-out infinite",
        "slide-in": "slide-in-right 300ms ease-out",
        "fade-in": "fade-in 200ms ease-out",
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
