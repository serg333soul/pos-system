import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
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
      // 1. Запити до КОШИКА йдуть на order_service (8000)
      '/api/cart': {
        target: 'http://order_service:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '') 
      },
      // 2. Всі інші запити (Categories, Units, Products) йдуть на product_service (8001)
      '/api': {
        target: 'http://product_service:8000', // Всередині Docker мережі вони всі слухають 8000
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})