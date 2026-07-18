import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  // The procedural scene is deferred; keep its expected vendor chunk separate from the dashboard.
  build: { chunkSizeWarningLimit: 850 },
});
