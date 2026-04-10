
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // 🔥 ВСІ запити на бекенд відправляємо в єдиний Nginx Gateway
      '/api': {
        target: 'http://localhost:8088', 
        changeOrigin: true
        // Зауважте: ми прибрали "rewrite", бо Nginx сам відрізає /api/ там, де це потрібно!
      }
    }
  }
})