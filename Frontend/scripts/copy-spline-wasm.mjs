/**
 * 将 Spline WASM 复制到 public，避免运行时从 unpkg CDN 加载失败
 */
import { copyFileSync, mkdirSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const outDir = join(root, 'public', 'spline-wasm')
const sources = [
  {
    from: join(root, 'node_modules', '@splinetool', 'modelling-wasm', 'build', 'process.wasm'),
    to: join(outDir, 'process.wasm'),
  },
  {
    from: join(root, 'node_modules', '@splinetool', 'ui-wasm', 'build', 'ui.wasm'),
    to: join(outDir, 'ui.wasm'),
  },
]

mkdirSync(outDir, { recursive: true })

for (const { from, to } of sources) {
  if (!existsSync(from)) {
    console.error(`[copy-spline-wasm] missing: ${from}`)
    console.error('Run npm install first.')
    process.exit(1)
  }
  copyFileSync(from, to)
  console.log(`[copy-spline-wasm] ${to}`)
}
