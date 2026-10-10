import { createI18n } from 'vue-i18n'
import en from './en.json'
import zh from './zh.json'

export type Locale = 'zh' | 'en'

export function detectLocale(): Locale {
  const saved = typeof localStorage !== 'undefined' ? (localStorage.getItem('ugclient.locale') ?? localStorage.getItem('uclient.locale')) : null
  if (saved === 'zh' || saved === 'en') return saved
  return typeof navigator !== 'undefined' && navigator.language.startsWith('zh') ? 'zh' : 'en'
}

export const i18n = createI18n({ legacy: false, locale: detectLocale(), fallbackLocale: 'en', messages: { en, zh } })
