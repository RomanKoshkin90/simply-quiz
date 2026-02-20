import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    include: ['framer-motion'],
  },
  build: {
    commonjsOptions: {
      include: [/framer-motion/, /node_modules/],
    },
  },
  server: {
    host: '0.0.0.0',  // Позволяет доступ из локальной сети
    port: 5173,  // Стандартный порт Vite
    allowedHosts: [
      '4eda1407452e.ngrok-free.app',  // ngrok frontend URL
      '.ngrok-free.app',  // Разрешаем все ngrok домены
      '.ngrok.io',  // На случай если используешь другой ngrok домен
    ],
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8086',
        changeOrigin: true,
      },
    },
  },
})
