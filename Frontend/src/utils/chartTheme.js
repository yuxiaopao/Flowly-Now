const SERIES_CSS_VARS = [
  '--accent-violet',
  '--accent-emerald',
  '--accent-amber',
  '--color-danger',
  '--accent-blue',
  '--accent-cyan',
]

const FALLBACK_SERIES = [
  '#8b5cf6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#3b82f6',
  '#06b6d4',
]

export function getCssColor(varName, fallback = '') {
  if (typeof document === 'undefined') {
    return fallback
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(varName).trim()
  return value || fallback
}

export function getChartSeriesColors() {
  return SERIES_CSS_VARS.map((name, index) => getCssColor(name, FALLBACK_SERIES[index]))
}

export function getChartPrimaryColor() {
  return getCssColor('--color-primary', '#06b6d4')
}

export function getChartPrimaryFill() {
  return getCssColor('--color-primary-10', 'rgba(6, 182, 212, 0.1)')
}

export function getChartSuccessColor() {
  return getCssColor('--color-success', '#22c55e')
}

export function getChartSuccessFill() {
  return getCssColor('--accent-emerald-soft', 'rgba(34, 197, 94, 0.1)')
}

export function getChartWarningColor() {
  return getCssColor('--accent-amber', '#f59e0b')
}

export function getChartTextColor() {
  return getCssColor('--text-secondary', '#6b7280')
}

export function getChartAxisColor() {
  return getCssColor('--border-primary', '#e5e7eb')
}

export function getChartSplitLineColor() {
  return getCssColor('--border-secondary', '#f3f4f6')
}

export function getChartSurfaceColor() {
  return getCssColor('--bg-secondary', '#ffffff')
}

export function getChartForegroundColor() {
  return getCssColor('--text-primary', '#111827')
}

/** Shared palette for ECharts option builders */
export function getEchartsTheme() {
  return {
    primary: getChartPrimaryColor(),
    success: getChartSuccessColor(),
    warning: getChartWarningColor(),
    text: getChartTextColor(),
    foreground: getChartForegroundColor(),
    axis: getChartAxisColor(),
    splitLine: getChartSplitLineColor(),
    surface: getChartSurfaceColor(),
    series: getChartSeriesColors(),
  }
}
