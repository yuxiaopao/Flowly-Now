import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'path'

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const backendTarget = env.VITE_DEV_BACKEND_URL || 'http://127.0.0.1:8000'
  return ({
  base: mode === 'electron' ? './' : '/',
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: command === 'serve' ? 'src/auto-imports.d.ts' : false
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: command === 'serve' ? 'src/components.d.ts' : false
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5200,
    strictPort: true,
    host: true,
    proxy: {
      '^/api(?:/|$)': {
        target: backendTarget,
        changeOrigin: true,
      },
      '^/ws(?:/|$)': {
        target: backendTarget.replace(/^http/, 'ws'),
        ws: true,
        changeOrigin: true,
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler'
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          'vue-flow': ['@vue-flow/core', '@vue-flow/background', '@vue-flow/controls', '@vue-flow/minimap'],
          'echarts': ['echarts'],
          'spline': ['@splinetool/runtime'],
        }
      }
    }
  },
  optimizeDeps: {
    include: [
      '@splinetool/runtime',
      'three',
      '3d-force-graph',
    ],
  },
  assetsInclude: ['**/*.wasm'],
  })
})
