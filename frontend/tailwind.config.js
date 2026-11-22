/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {
    colors: {
      ink: '#070b12', panel: '#0e1622', line: '#223044', accent: '#00d7d7', cyan: '#00d7d7',
      brand: { cyan: '#00d7d7', pink: '#ff3b7c', coral: '#ff6b6b', navy: '#070b12' },
    },
    fontFamily: { display: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
    boxShadow: {
      glow: '0 0 38px rgba(0,215,215,.15)',
      'pink-glow': '0 0 38px rgba(255,59,124,.18)',
      card: '0 26px 80px rgba(0,0,0,.42)',
    },
  } },
  plugins: [],
}
