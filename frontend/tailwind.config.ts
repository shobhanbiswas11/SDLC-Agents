import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Brand: #009eda (cyan) on #ffffff (canvas).
        primary: {
          50: '#f0fbff',
          100: '#e0f6fd',
          200: '#b8ecfa',
          300: '#7dd9f3',
          400: '#33bfe6',
          500: '#009eda', // brand
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c3d66',
        },
        canvas: '#ffffff',
      },
    },
  },
  plugins: [],
};

export default config;
