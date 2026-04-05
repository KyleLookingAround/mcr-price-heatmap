import { defineConfig } from 'vite'

export default defineConfig({
  base: '/mcr-price-heatmap/',
  build: {
    outDir: 'dist',
    assetsInlineLimit: 0,
  },
  server: {
    port: 3000,
  },
})
