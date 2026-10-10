/** Save a text file: native dialog in Tauri, browser download otherwise. */
export async function saveText(defaultName: string, text: string): Promise<string | null> {
  const w = window as unknown as { __TAURI_INTERNALS__?: unknown }
  if (w.__TAURI_INTERNALS__) {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const { invoke } = await import('@tauri-apps/api/core')
    const path = await save({ defaultPath: defaultName })
    if (!path) return null
    await invoke('write_text_file', { path, contents: text })
    return path
  }
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv' }))
  const a = document.createElement('a')
  a.href = url
  a.download = defaultName
  a.click()
  URL.revokeObjectURL(url)
  return defaultName
}
