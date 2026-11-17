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
      resolvers: [ElementPlusResolver({ importStyle: false })],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: false
    }),
    Components({
      resolvers: [ElementPlusResolver({ importStyle: false })],
      dts: false
    })
  ],
  resolve: {
    alias: [
      { find: '@', replacement: path.resolve(__dirname, 'src') },
      { find: 'pinia', replacement: path.resolve(__dirname, 'node_modules/pinia/dist/pinia.mjs') },
      { find: 'vue', replacement: path.resolve(__dirname, 'node_modules/vue/dist/vue.runtime.esm-bundler.js') },
      { find: 'vue-router', replacement: path.resolve(__dirname, 'node_modules/vue-router/dist/vue-router.mjs') },
      { find: /^@vue-flow\/core$/, replacement: path.resolve(__dirname, 'node_modules/@vue-flow/core/dist/vue-flow-core.mjs') },
      { find: '@vue/test-utils', replacement: path.resolve(__dirname, 'node_modules/@vue/test-utils/dist/vue-test-utils.esm-bundler.mjs') },
    ]
  },
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['../tests/frontend/vitest/**/*.test.{js,ts}', '../tests/frontend/vitest/**/*.spec.{js,ts}'],
    exclude: ['../tests/frontend/e2e/**'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{js,ts,vue}'],
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
    setupFiles: [path.resolve(__dirname, '../tests/frontend/vitest/setup.js')],
    testTimeout: 10000,
    hookTimeout: 10000
  },
  server: {
    port: 5200,
    strictPort: true,
    host: true,
    fs: {
      allow: [path.resolve(__dirname, '..')]
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler'
      }
    }
  }
})
