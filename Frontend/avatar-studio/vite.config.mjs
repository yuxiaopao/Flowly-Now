import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  base: './',
  plugins: [vue(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  build: {
    target: ['es2020', 'edge88', 'firefox78', 'chrome87', 'safari14'],
    outDir: fileURLToPath(new URL('../public/avatar-studio', import.meta.url)),
    emptyOutDir: true,
  },
})
