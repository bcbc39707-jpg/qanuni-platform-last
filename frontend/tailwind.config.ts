import type { Config } from 'tailwindcss'
const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        primary: { 50: '#eff6ff', 100: '#dbeafe', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8', 900: '#1e3a5f' },
        accent: { gold: '#d4af37', green: '#10b981' },
      },
      fontFamily: { arabic: ['Tajawal', 'sans-serif'] },
    },
  },
  plugins: [],
}
export default config
