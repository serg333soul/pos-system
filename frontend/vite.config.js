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
      // 1. Запити до КОШИКА йдуть на order_service
      '/api/cart': {
        target: 'http://order_service:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      
      // 🔥 НОВЕ ПРАВИЛО: Всі запити по фінансах йдуть на новий мікросервіс!
      '/api/finance': {
        target: 'http://finance_api:8002', // Вказуємо контейнер нашої нової БД
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },

      // 🔥 СКЛАД (Inventory)
      '/api/ingredients': {
        target: 'http://inventory_api:8004',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/api/consumables': {
        target: 'http://inventory_api:8004',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/api/units': {
        target: 'http://inventory_api:8004',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/api/history': {
        target: 'http://inventory_api:8004',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },

      // 3. Всі ІНШІ запити (Клієнти, Склад, Товари) йдуть на старий product_service
      '/api': {
        target: 'http://product_service:8000', 
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})