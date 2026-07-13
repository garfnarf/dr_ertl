import { defineConfig } from 'astro/config';
import yaml from '@rollup/plugin-yaml';

export default defineConfig({
  site: 'https://praxis-dr-ertl.de',
  trailingSlash: 'ignore',
  vite: {
    plugins: [yaml()],
  },
});
