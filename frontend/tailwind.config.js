/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Светлая палитра
        'primary': '#0ea5e9',
        'primary-dark': '#0284c7',
        'primary-light': '#38bdf8',
        'accent': '#06b6d4',
        // Серые
        'slate': {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
        // Голосовые типы
        'bass': '#0ea5e9',
        'baritone': '#0891b2',
        'tenor': '#06b6d4',
        'alto': '#14b8a6',
        'mezzo': '#10b981',
        'soprano': '#22c55e',
      },
      fontFamily: {
        'display': ['Outfit', 'sans-serif'],
        'body': ['Manrope', 'sans-serif'],
        'mono': ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
