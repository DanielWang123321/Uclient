import { describe, expect, it } from 'vitest'
import en from '../src/i18n/en.json'
import zh from '../src/i18n/zh.json'

function keys(o: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(o).flatMap(([k, v]) =>
    v && typeof v === 'object' ? keys(v as Record<string, unknown>, `${prefix}${k}.`) : [`${prefix}${k}`],
  )
}

describe('i18n', () => {
  it('zh and en have identical keys', () => {
    expect(keys(zh).sort()).toEqual(keys(en).sort())
  })
  it('states the personal-project disclaimer in both languages', () => {
    expect(en.app.personal).toMatch(/not an official UFACTORY product/)
    expect(zh.app.personal).toMatch(/非 UFACTORY 官方产品/)
  })
})
