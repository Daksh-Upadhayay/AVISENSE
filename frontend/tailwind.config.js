/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        page: '#0d0d0d',
        surface: { DEFAULT: '#1a1a19', raised: '#222220', hover: '#2a2a28' },
        line: { DEFAULT: '#2c2c2a', strong: '#383835' },
        ink: { DEFAULT: '#ffffff', secondary: '#c3c2b7', muted: '#898781' },
        accent: { DEFAULT: '#3987e5', strong: '#2a78d6', soft: '#86b6ef' },
        good: '#0ca30c',
        warning: '#fab219',
        critical: '#d03b3b',
        shorten: '#e66767',
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', '"Segoe UI"', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
}
