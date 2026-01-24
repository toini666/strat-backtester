/** @type {import('tailwindcss').Config} */
export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {
        colors: {
          nebular: {
            900: '#0B0F19', // Deepest background
            800: '#111827', // Secondary background
            700: '#1F2937', // Card background
            600: '#374151', // Borders
          },
          primary: {
            500: '#3B82F6', // Blue
            600: '#2563EB',
          },
          accent: {
            500: '#8B5CF6', // Purple
            600: '#7C3AED',
          }
        },
        fontFamily: {
          sans: ['Inter', 'system-ui', 'sans-serif'],
          mono: ['JetBrains Mono', 'Menlo', 'monospace'],
        },
      },
    },
    plugins: [],
  }
