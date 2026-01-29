/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: '#050505',
        emerald: '#5EF7A6',
        'cyber-lime': '#FFFF21',
      },
      fontFamily: {
        mono: ['Space Grotesk', 'monospace'],
        sans: ['Inter', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px #5EF7A6, 0 0 10px #5EF7A6' },
          '100%': { boxShadow: '0 0 20px #5EF7A6, 0 0 30px #5EF7A6' },
        }
      }
    },
  },
  plugins: [],
}
