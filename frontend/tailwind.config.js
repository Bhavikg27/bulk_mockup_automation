/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#09090b", // Zinc 950
        surface: "#18181b", // Zinc 900
        primary: {
          DEFAULT: "#8b5cf6", // Violet 500
          foreground: "#ffffff",
        },
        secondary: {
          DEFAULT: "#06b6d4", // Cyan 500
          foreground: "#ffffff",
        },
        accent: {
          DEFAULT: "#f43f5e", // Rose 500
          foreground: "#ffffff",
        },
        muted: "#71717a", // Zinc 500
      },
      fontFamily: {
        sans: ['"Outfit"', 'sans-serif'],
        display: ['"Space Grotesk"', 'sans-serif'],
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: 1, boxShadow: '0 0 20px rgba(139, 92, 246, 0.5)' },
          '50%': { opacity: .7, boxShadow: '0 0 10px rgba(139, 92, 246, 0.2)' },
        },
        fadeIn: {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: 0 },
          '100%': { transform: 'translateY(0)', opacity: 1 },
        },
      },
      boxShadow: {
        'neon': '0 0 20px rgba(139, 92, 246, 0.3)',
        'neon-hover': '0 0 30px rgba(139, 92, 246, 0.5)',
      }
    },
  },
  plugins: [],
};
