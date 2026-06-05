/**
 * 轮询、防抖、节流工具函数
 */

/**
 * 轮询管理器
 */
export class PollingManager {
  private timer: ReturnType<typeof setTimeout> | null = null
  private isRunning = false
  private attempts = 0
  private maxAttempts: number
  private interval: number

  constructor(options: {
    interval?: number
    maxAttempts?: number
  } = {}) {
    this.interval = options.interval || 2000
    this.maxAttempts = options.maxAttempts || 30
  }

  /**
   * 开始轮询
   */
  start(callback: () => Promise<boolean | void>) {
    if (this.isRunning) return

    this.isRunning = true
    this.attempts = 0

    const poll = async () => {
      if (!this.isRunning) return

      try {
        const shouldContinue = await callback()
        this.attempts++

        if (shouldContinue === false) {
          this.stop()
          return
        }

        if (this.attempts >= this.maxAttempts) {
          this.stop()
          return
        }

        this.timer = setTimeout(poll, this.interval)
      } catch {
        this.stop()
      }
    }

    poll()
  }

  /**
   * 停止轮询
   */
  stop() {
    this.isRunning = false
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
  }

  /**
   * 暂停轮询
   */
  pause() {
    this.isRunning = false
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
  }

  /**
   * 恢复轮询
   */
  resume(callback: () => Promise<boolean | void>) {
    if (this.isRunning) return
    this.start(callback)
  }

  /**
   * 获取状态
   */
  getStatus() {
    return {
      isRunning: this.isRunning,
      attempts: this.attempts,
      maxAttempts: this.maxAttempts
    }
  }
}

/**
 * 创建轮询钩子（Vue 组合式函数）
 */
export function createPolling(options: {
  interval?: number
  maxAttempts?: number
  onResult?: (result: unknown) => boolean | void
  onError?: (error: Error) => void
} = {}) {
  const {
    interval = 2000,
    maxAttempts = 30,
    onResult,
    onError
  } = options

  const polling = new PollingManager({ interval, maxAttempts })

  const start = (callback: () => Promise<boolean | void>) => {
    polling.start(async () => {
      try {
        const result = await callback()
        const shouldContinue = onResult ? onResult(result) : result
        return shouldContinue as boolean
      } catch (error) {
        onError?.(error as Error)
        return false
      }
    })
  }

  const stop = () => polling.stop()
  const pause = () => polling.pause()
  const resume = (callback: () => Promise<boolean | void>) => polling.resume(callback)
  const getStatus = () => polling.getStatus()

  return {
    start,
    stop,
    pause,
    resume,
    getStatus,
    polling
  }
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null

  return function (this: unknown, ...args: Parameters<T>) {
    const context = this

    if (timeout) {
      clearTimeout(timeout)
    }

    timeout = setTimeout(() => {
      func.apply(context, args)
    }, wait)
  }
}

/**
 * 带立即执行的防抖
 */
export function debounceImmediate<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number,
  immediate = false
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null

  return function (this: unknown, ...args: Parameters<T>) {
    const context = this

    const callNow = immediate && !timeout

    if (timeout) {
      clearTimeout(timeout)
    }

    timeout = setTimeout(() => {
      timeout = null
      if (!immediate) {
        func.apply(context, args)
      }
    }, wait)

    if (callNow) {
      func.apply(context, args)
    }
  }
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false
  let lastArgs: Parameters<T> | null = null

  return function (this: unknown, ...args: Parameters<T>) {
    const context = this

    if (!inThrottle) {
      func.apply(context, args)
      inThrottle = true

      setTimeout(() => {
        inThrottle = false
        if (lastArgs) {
          func.apply(context, lastArgs)
          lastArgs = null
        }
      }, limit)
    } else {
      lastArgs = args
    }
  }
}

/**
 * 一次执行（带锁定）
 */
export function once<T extends (...args: unknown[]) => unknown>(
  func: T
): (...args: Parameters<T>) => ReturnType<T> | undefined {
  let called = false
  let result: ReturnType<T>

  return function (this: unknown, ...args: Parameters<T>): ReturnType<T> | undefined {
    if (!called) {
      called = true
      result = func.apply(this, args) as ReturnType<T>
      return result
    }
    return result
  }
}

/**
 * 重试函数
 */
export async function retry<T>(
  fn: () => Promise<T>,
  options: {
    maxAttempts?: number
    delay?: number
    backoff?: number
    onRetry?: (attempt: number, error: Error) => void
  } = {}
): Promise<T> {
  const {
    maxAttempts = 3,
    delay = 1000,
    backoff = 2,
    onRetry
  } = options

  let lastError: Error

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error as Error

      if (attempt < maxAttempts) {
        onRetry?.(attempt, lastError)

        const waitTime = delay * Math.pow(backoff, attempt - 1)
        await new Promise(resolve => setTimeout(resolve, waitTime))
      }
    }
  }

  throw lastError!
}

/**
 * 超时包装器
 */
export function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  timeoutError = new Error('Operation timed out')
): Promise<T> {
  return Promise.race([
    promise,
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(timeoutError), timeoutMs)
    )
  ])
}
