/**
 * Global error handler setup for Vue app.
 * Handles uncaught errors, unhandled promise rejections, and component errors.
 */


// Error reporting function - replace with your monitoring service
function reportError(error, context = {}) {
  try {
    const payload = {
      type: context.type || 'unknown',
      message: error?.message || String(error),
      stack: error?.stack || '',
      url: typeof window !== 'undefined' ? window.location.href : '',
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
      timestamp: new Date().toISOString(),
      ...context,
    }

    // Send to monitoring endpoint if available
    if (typeof window !== 'undefined' && window.__ERROR_REPORT_URL__) {
      fetch(window.__ERROR_REPORT_URL__, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(() => {})
    }

    // Also log to console in development
    if (import.meta.env.DEV) {
      console.error('[Global Error]', payload)
    }
  } catch {
    // Never let reporting itself crash
  }
}

export function setupGlobalErrorHandler(app) {
  // Vue component error handler
  app.config.errorHandler = (err, instance, info) => {
    reportError(err, {
      type: 'vue_component',
      componentName: instance?.$options?.name || instance?.$options?.__name || 'Anonymous',
      componentInfo: info,
    })
  }

  // Unhandled promise rejections
  if (typeof window !== 'undefined') {
    window.addEventListener('unhandledrejection', (event) => {
      const error = event.reason
      reportError(error, { type: 'unhandled_promise_rejection' })
    })

    // Global JS errors
    window.addEventListener('error', (event) => {
      reportError(event.error || new Error(event.message), {
        type: 'global_error',
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      })
    })
  }
}

export function reportComponentError(error, context = {}) {
  reportError(error, { type: 'component_error', ...context })
}

export default { setupGlobalErrorHandler, reportComponentError, reportError }
