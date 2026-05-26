import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  base: '/',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0', // 监听所有网卡，确保在容器/远程环境中可访问
    port: 5173,
    strictPort: true, // 确保只使用指定端口，如果被占用则退出
    hmr: {
      clientPort: 5173, // 强制 HMR 使用标准端口，避免产生随机高位端口
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000', // 根据实际后端地址修改
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue', 'vue-router'],
          'icons': ['lucide-vue-next']
        }
      }
    }
  }
})
