/** Tailwind 构建配置：与 research_workbench.html 内联 theme.extend 保持一致（用于离线 CSS，消除 CDN 控制台告警）。 */
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./research_workbench.html'],
  theme: {
    extend: {
      colors: {
        dopamine: {
          orange: '#FF8C42',
          pink: '#FF6B8B',
          yellow: '#F9C74F',
          mint: '#43AA8B',
          sky: '#4D9DE0',
          purple: '#9B5DE5',
          coral: '#F48C6E',
          lime: '#A7C957',
        },
        calm: {
          ink: '#45495F',
          mute: '#8A8FA6',
          bg: '#F7F8FC',
          line: '#ECEEF5',
        },
      },
      boxShadow: {
        soft: '0 18px 45px -22px rgba(0,0,0,.16)',
        floaty: '0 24px 60px -28px rgba(0,0,0,.22)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
