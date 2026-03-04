/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Syne', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
      },
      colors: {
        terminal: {
          bg: '#0a0e13',
          surface: '#0f1419',
          border: '#1e2d3d',
          accent: '#00d9ff',
          green: '#39d353',
          red: '#ff4757',
          yellow: '#ffa502',
          purple: '#a78bfa',
          muted: '#4a5568',
          text: '#c9d1d9',
        }
      },
      keyframes: {
        fadeSlideUp: {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        }
      },
      animation: {
        message: 'fadeSlideUp 0.35s ease forwards',
        scan: 'scan 8s linear infinite',
      }
    }
  },
  plugins: []
}