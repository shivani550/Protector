/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        head: ['Poppins', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['Georgia', 'serif'],
      },
      colors: {
        'cf-plum': '#b6a7de',
        'cf-plum-48': 'rgba(182, 167, 222, 0.48)',
        'cf-steel': '#8275ab',
        'cf-violet': {
          600: '#644790',
          700: '#543c76',
          900: '#35264f',
        },
        'cf-lavender': '#e4e0f4',
        'cf-thistle': '#cec6ea',
        'cf-bg': '#f7f6fc',
        'cf-bg-2': '#f0eef9',
        'cf-surface': '#ffffff',
        'cf-surface-2': '#fafafb',
        'cf-text': '#111111',
        'cf-text-2': '#585161',
        'cf-text-3': '#68686b',
        'cf-muted': '#a8a8ac',
        'cf-border': '#e6e6e6',
        'cf-border-2': '#eaebee',
        'cf-success': '#269d72',
        'cf-success-bg': '#e6f5ef',
        'cf-warn': '#b7791f',
        'cf-warn-bg': '#fdf3dc',
        'cf-danger': '#c0392b',
        'cf-danger-bg': '#fbe9e7',
        'cf-info': '#644790',
        'cf-info-bg': '#ede9f8',
      },
      borderRadius: {
        'cf-xs': '4px',
        'cf-sm': '8px',
        'cf-md': '16px',
        'cf-lg': '22px',
        'cf-xl': '32px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(0,0,0,.06), 0 4px 16px rgba(0,0,0,.06)',
        'card-hover': '0 2px 4px rgba(0,0,0,.06), 0 8px 24px rgba(100,71,144,.1)',
      },
    },
  },
  plugins: [],
}
