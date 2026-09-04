import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  const RENDER_BACKEND_URL = 'https://shravya-s-razorpay-build.onrender.com'
  const LOCAL_BACKEND_URL = 'http://127.0.0.1:8000'

  // Default to Render backend, or override via VITE_BACKEND_URL in .env
  const backendTarget = env.VITE_BACKEND_URL || RENDER_BACKEND_URL

  return {
    plugins: [
      react(),
      tailwindcss(),
    ],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
        '/api-render': {
          target: RENDER_BACKEND_URL,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api-render/, ''),
        },
        '/api-local': {
          target: LOCAL_BACKEND_URL,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api-local/, ''),
        },
      },
    },
  }
})

