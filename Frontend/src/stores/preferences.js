import { defineStore } from 'pinia'
import { reactive } from 'vue'
import { PREFERENCE_CONFIG } from '@/config/personalCenter'

export function readPreferences(storage = localStorage) {
  try {
    const saved = JSON.parse(storage.getItem(PREFERENCE_CONFIG.storageKey) || '{}')
    return saved && typeof saved === 'object' && !Array.isArray(saved) ? saved : {}
  } catch {
    return {}
  }
}

export const usePreferencesStore = defineStore('preferences', () => {
  const saved = readPreferences()
  const editor = reactive(Object.fromEntries(Object.entries(PREFERENCE_CONFIG.defaults)
    .map(([key, value]) => [key, typeof saved[key] === 'boolean' ? saved[key] : value])))

  function save(values) {
    const next = Object.fromEntries(Object.keys(PREFERENCE_CONFIG.defaults)
      .map(key => [key, typeof values[key] === 'boolean' ? values[key] : editor[key]]))
    localStorage.setItem(PREFERENCE_CONFIG.storageKey, JSON.stringify({ ...readPreferences(), ...next }))
    Object.assign(editor, next)
  }

  return { editor, save }
})
