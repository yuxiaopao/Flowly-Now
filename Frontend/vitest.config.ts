import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'path'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts'
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts'
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['../tests/frontend/vitest/**/*.test.{js,ts}', '../tests/frontend/vitest/**/*.spec.{js,ts}'],
    exclude: ['../tests/frontend/e2e/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/**',
        'dist/**',
        'src/auto-imports.d.ts',
        'src/components.d.ts',
        '**/*.config.{js,ts}',
        '../tests/**'
      ]
    },
    setupFiles: ['../tests/frontend/vitest/setup.js'],
    testTimeout: 10000,
    hookTimeout: 10000
  },
  server: {
    port: 5200,
    strictPort: true,
    host: true
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler'
      }
    }
  }
})
