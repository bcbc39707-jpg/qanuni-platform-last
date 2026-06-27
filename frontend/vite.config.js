import { defineConfig } from 'vite';
import { resolve } from 'path';
import fs from 'fs';

export default defineConfig({
  root: '.',
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        login: resolve(__dirname, 'login.html'),
        register: resolve(__dirname, 'register.html'),
        app: resolve(__dirname, 'app.html'),
        pricing: resolve(__dirname, 'pricing.html'),
        dashboard: resolve(__dirname, 'dashboard.html'),
        search: resolve(__dirname, 'search.html'),
        library: resolve(__dirname, 'library.html'),
        generator: resolve(__dirname, 'generator.html'),
        analyzer: resolve(__dirname, 'analyzer.html'),
        settings: resolve(__dirname, 'settings.html'),
        lawViewer: resolve(__dirname, 'law-viewer.html'),
        adminUpload: resolve(__dirname, 'admin-upload.html'),
      }
    }
  },
  plugins: [
    {
      name: 'copy-api-js',
      closeBundle() {
        try {
          fs.copyFileSync(resolve(__dirname, 'api.js'), resolve(__dirname, 'dist/api.js'));
          console.log('Successfully copied api.js to dist/');
        } catch (err) {
          console.error('Failed to copy api.js:', err);
        }
      }
    }
  ],
  server: {
    port: 3000,
    open: true
  }
});
