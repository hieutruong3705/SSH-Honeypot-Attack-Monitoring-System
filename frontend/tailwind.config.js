/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        soft: {
          bg: '#f0f9ff',       // sky-50
          card: '#ffffff',     // white
          border: '#bae6fd',   // sky-200
          text: '#475569',     // slate-600
          textHover: '#0369a1',// sky-700
          red: '#ef4444',
          yellow: '#eab308',
          green: '#10b981',
        }
      }
    },
  },
  plugins: [],
}
