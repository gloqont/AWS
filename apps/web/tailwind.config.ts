import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        gloqont: {
          bg: '#0a0a0c',
          card: '#0F0F12',
          indigo: '#6366f1',
          purple: '#a855f7',
          emerald: '#10b981',
          cyan: '#06b6d4',
        },
      },
      animation: {
        'aurora': 'aurora 15s ease infinite',
        'gradient-text': 'gradient-shift 4s ease infinite',
        'shimmer': 'shimmer 2s ease-in-out infinite',
        'rotate-glow': 'rotate-glow 4s linear infinite',
        'orbit': 'orbit 20s linear infinite',
        'orbit-reverse': 'orbit-reverse 25s linear infinite',
        'draw-line': 'draw-line 2s ease-out forwards',
        'slide-up': 'slide-up 0.7s ease-out forwards',
        'scale-in': 'scale-in 0.5s ease-out forwards',
        'particle': 'particle-float 8s ease-in-out infinite',
        'glow-border': 'glow-border 3s ease-in-out infinite',
        'ticker': 'ticker-scroll 30s linear infinite',
        'breathe': 'breathe 4s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
        'blob': 'blob 7s infinite',
      },
      backgroundImage: {
        'gradient-mesh': 'radial-gradient(at 40% 20%, hsla(228,80%,55%,0.15) 0px, transparent 50%), radial-gradient(at 80% 0%, hsla(160,80%,45%,0.12) 0px, transparent 50%), radial-gradient(at 0% 50%, hsla(270,80%,55%,0.1) 0px, transparent 50%), radial-gradient(at 80% 50%, hsla(340,80%,55%,0.08) 0px, transparent 50%), radial-gradient(at 0% 100%, hsla(228,80%,55%,0.1) 0px, transparent 50%)',
      },
    },
  },
  plugins: [],
};
export default config;
