/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: { colors: { ink: '#090d12', panel: '#0f151c', line: '#202b36', accent: '#35e0a1', cyan: '#32c5ff' }, boxShadow: { glow: '0 0 40px rgba(53,224,161,.12)' } } },
  plugins: [],
}

