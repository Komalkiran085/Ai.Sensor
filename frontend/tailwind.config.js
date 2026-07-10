/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        danger: { 50: '#fef2f2', 500: '#ef4444', 700: '#b91c1c' },
        warn: { 50: '#fffbeb', 500: '#f59e0b', 700: '#b45309' },
        safe: { 50: '#f0fdf4', 500: '#22c55e', 700: '#15803d' },
      },
      animation: {
        'pulse-alert': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
