/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#17202a',
        canvas: '#f4f6f8',
        brand: '#315df5',
      },
      boxShadow: {
        panel: '0 1px 2px rgba(15,23,42,.04), 0 8px 24px rgba(15,23,42,.06)',
      },
    },
  },
  plugins: [],
}
