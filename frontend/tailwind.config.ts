import type { Config } from "tailwindcss";

const c = (v: string) => `hsl(var(--${v}))`;

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: c("border"), input: c("input"), ring: c("ring"),
        background: c("background"), foreground: c("foreground"),
        primary: { DEFAULT: c("primary"), foreground: c("primary-foreground") },
        secondary: { DEFAULT: c("secondary"), foreground: c("secondary-foreground") },
        destructive: { DEFAULT: c("destructive"), foreground: c("destructive-foreground") },
        muted: { DEFAULT: c("muted"), foreground: c("muted-foreground") },
        accent: { DEFAULT: c("accent"), foreground: c("accent-foreground") },
        card: { DEFAULT: c("card"), foreground: c("card-foreground") },
        popover: { DEFAULT: c("popover"), foreground: c("popover-foreground") },
        positive: c("positive"), negative: c("negative"), warning: c("warning"),
        chart: { 1: c("chart-1"), 2: c("chart-2"), 3: c("chart-3"), 4: c("chart-4"), 5: c("chart-5") },
      },
      borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)", sm: "calc(var(--radius) - 4px)" },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
