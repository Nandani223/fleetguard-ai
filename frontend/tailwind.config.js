/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#FBF7ED',
        surface: '#FFFFFF',
        'surface-sunken': '#F5F0E1',
        line: '#EBE3D0',
        ink: '#211E17',
        'ink-dim': '#7A7364',
        'ink-faint': '#A69C87',
        brand: {
          DEFAULT: '#fa7efe',
          soft: '#FBE7D9',
          dim: '#f450ec',
        },
        teal: {
          DEFAULT: '#0EA5A5',
          soft: '#E3F7F5',
        },
        risk: {
          green: '#16A34A',
          'green-soft': '#E7F7EC',
          amber: '#D97706',
          'amber-soft': '#FDF1E1',
          red: '#E5484D',
          'red-soft': '#FCE8E8',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(23, 23, 31, 0.04), 0 1px 12px rgba(23, 23, 31, 0.03)',
        pop: '0 4px 20px rgba(109, 79, 235, 0.18)',
      },
    },
  },
  plugins: [],
}
