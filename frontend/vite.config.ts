import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: true,
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: true,
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true,
        configure: (proxy, _options) => {
          // 可按需启用以下调试日志
          // proxy.on('error', (err, _req, _res) => console.log('proxy error', err))
          // proxy.on('proxyReq', (proxyReq, req, _res) => console.log('proxyReq', req.method, req.url))
          // proxy.on('proxyRes', (proxyRes, req, _res) => console.log('proxyRes', proxyRes.statusCode, req.url))
        },
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    
  },
})