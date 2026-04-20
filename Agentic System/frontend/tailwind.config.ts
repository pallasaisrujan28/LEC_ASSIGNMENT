import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        syne:   ['var(--font-syne)',    'sans-serif'],
        outfit: ['var(--font-outfit)',  'sans-serif'],
        mono:   ['var(--font-mono)',    'monospace'],
      },
      colors: {
        bg: {
          base:  '#07070f',
          1:     '#0c0c18',
          2:     '#111120',
          3:     '#16162a',
          4:     '#1c1c35',
        },
        accent: {
          DEFAULT: '#00e5ff',
          dim:     'rgba(0,229,255,0.1)',
          glow:    'rgba(0,229,255,0.2)',
        },
        border: {
          DEFAULT: 'rgba(255,255,255,0.05)',
          bright:  'rgba(255,255,255,0.10)',
          accent:  'rgba(0,229,255,0.20)',
        },
      },
      keyframes: {
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)'    },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-left': {
          '0%':   { opacity: '0', transform: 'translateX(-10px)' },
          '100%': { opacity: '1', transform: 'translateX(0)'     },
        },
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(0,229,255,0.15)' },
          '50%':       { boxShadow: '0 0 40px rgba(0,229,255,0.35)' },
        },
        'dot-bounce': {
          '0%, 80%, 100%': { transform: 'scale(0.8)', opacity: '0.3' },
          '40%':            { transform: 'scale(1.2)', opacity: '1'   },
        },
        'status-pulse': {
          '0%, 100%': { opacity: '1'   },
          '50%':       { opacity: '0.4' },
        },
      },
      animation: {
        'fade-up':      'fade-up 0.35s ease both',
        'fade-in':      'fade-in 0.3s ease both',
        'slide-left':   'slide-left 0.3s ease both',
        'glow-pulse':   'glow-pulse 2.5s ease-in-out infinite',
        'dot-1':        'dot-bounce 1.2s infinite 0.0s',
        'dot-2':        'dot-bounce 1.2s infinite 0.2s',
        'dot-3':        'dot-bounce 1.2s infinite 0.4s',
        'status-pulse': 'status-pulse 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
export default config;
