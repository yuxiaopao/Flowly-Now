/**
 * 性能优化工具函数
 */

// 防抖
export function debounce(fn, delay = 300) {
  let timer = null
  return function (...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  }
}

// 节流
export function throttle(fn, delay = 300) {
  let lastTime = 0
  return function (...args) {
    const now = Date.now()
    if (now - lastTime >= delay) {
      lastTime = now
      fn.apply(this, args)
    }
  }
}

// 延迟执行
export function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// 异步队列
export class AsyncQueue {
  constructor(concurrency = 1) {
    this.concurrency = concurrency
    this.queue = []
    this.running = 0
  }

  async add(task) {
    return new Promise((resolve, reject) => {
      this.queue.push({ task, resolve, reject })
      this.process()
    })
  }

  async process() {
    while (this.running < this.concurrency && this.queue.length > 0) {
      const { task, resolve, reject } = this.queue.shift()
      this.running++
      task()
        .then(resolve)
        .catch(reject)
        .finally(() => {
          this.running--
          this.process()
        })
    }
  }
}

// 内存缓存
export class MemoryCache {
  constructor(maxSize = 100, ttl = 60000) {
    this.cache = new Map()
    this.maxSize = maxSize
    this.ttl = ttl
  }

  get(key) {
    const item = this.cache.get(key)
    if (!item) return null

    if (Date.now() > item.expires) {
      this.cache.delete(key)
      return null
    }

    return item.value
  }

  set(key, value) {
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value
      this.cache.delete(firstKey)
    }

    this.cache.set(key, {
      value,
      expires: Date.now() + this.ttl
    })
  }

  has(key) {
    return this.get(key) !== null
  }

  delete(key) {
    return this.cache.delete(key)
  }

  clear() {
    this.cache.clear()
  }
}

// 虚拟滚动
export class VirtualList {
  constructor(options = {}) {
    this.itemHeight = options.itemHeight || 50
    this.containerHeight = options.containerHeight || 400
    this.items = options.items || []
    this.visibleCount = Math.ceil(this.containerHeight / this.itemHeight) + 2
    this.scrollTop = 0
  }

  get startIndex() {
    return Math.floor(this.scrollTop / this.itemHeight)
  }

  get endIndex() {
    return Math.min(this.startIndex + this.visibleCount, this.items.length)
  }

  get visibleItems() {
    return this.items.slice(this.startIndex, this.endIndex)
  }

  get totalHeight() {
    return this.items.length * this.itemHeight
  }

  get offsetY() {
    return this.startIndex * this.itemHeight
  }

  handleScroll(scrollTop) {
    this.scrollTop = scrollTop
  }
}

// 大文件处理
export async function processLargeFile(file, chunkSize = 1024 * 1024, onProgress) {
  const totalChunks = Math.ceil(file.size / chunkSize)
  const results = []

  for (let i = 0; i < totalChunks; i++) {
    const start = i * chunkSize
    const end = Math.min(start + chunkSize, file.size)
    const chunk = file.slice(start, end)

    // Process chunk
    const reader = new FileReader()
    const content = await new Promise((resolve, reject) => {
      reader.onload = e => resolve(e.target.result)
      reader.onerror = reject
      reader.readAsText(chunk)
    })

    results.push(content)

    if (onProgress) {
      onProgress({
        current: i + 1,
        total: totalChunks,
        percent: Math.round(((i + 1) / totalChunks) * 100)
      })
    }
  }

  return results.join('')
}

// 图片优化
export function optimizeImage(file, maxWidth = 1920, maxHeight = 1080, quality = 0.8) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      let width = img.width
      let height = img.height

      if (width > maxWidth) {
        height = (height * maxWidth) / width
        width = maxWidth
      }

      if (height > maxHeight) {
        width = (width * maxHeight) / height
        height = maxHeight
      }

      canvas.width = width
      canvas.height = height

      const ctx = canvas.getContext('2d')
      ctx.drawImage(img, 0, 0, width, height)

      canvas.toBlob(
        blob => resolve(blob),
        'image/jpeg',
        quality
      )
    }
    img.onerror = reject
    img.src = URL.createObjectURL(file)
  })
}

// 深拷贝
export function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj
  if (obj instanceof Date) return new Date(obj)
  if (obj instanceof Array) return obj.map(item => deepClone(item))
  if (obj instanceof Object) {
    const cloned = {}
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        cloned[key] = deepClone(obj[key])
      }
    }
    return cloned
  }
}

// 扁平化对象
export function flattenObject(obj, prefix = '') {
  const result = {}

  for (const key in obj) {
    const newKey = prefix ? `${prefix}.${key}` : key
    const value = obj[key]

    if (value && typeof value === 'object' && !Array.isArray(value) && !(value instanceof Date)) {
      Object.assign(result, flattenObject(value, newKey))
    } else {
      result[newKey] = value
    }
  }

  return result
}

// 性能度量
export class PerformanceMonitor {
  constructor() {
    this.marks = new Map()
    this.measures = []
  }

  mark(name) {
    this.marks.set(name, performance.now())
  }

  measure(name, startMark, endMark) {
    const start = this.marks.get(startMark) || 0
    const end = this.marks.get(endMark) || performance.now()
    const duration = end - start

    this.measures.push({
      name,
      duration,
      timestamp: Date.now()
    })

    return duration
  }

  getMeasures() {
    return [...this.measures]
  }

  clear() {
    this.marks.clear()
    this.measures = []
  }
}

// 资源加载
export async function preloadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = url
  })
}

export async function preloadFonts(fonts) {
  return Promise.all(
    fonts.map(font => document.fonts.load(font)))
}

// 懒加载图片
export function lazyLoadImage(element, src) {
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target
          img.src = src
          observer.unobserve(img)
        }
      })
    })
    observer.observe(element)
  } else {
    element.src = src
  }
}

export default {
  debounce,
  throttle,
  delay,
  AsyncQueue,
  MemoryCache,
  VirtualList,
  processLargeFile,
  optimizeImage,
  deepClone,
  flattenObject,
  PerformanceMonitor,
  preloadImage,
  preloadFonts,
  lazyLoadImage
}
