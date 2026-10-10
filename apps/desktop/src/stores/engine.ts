import { defineStore } from 'pinia'
import { markRaw, ref, shallowRef } from 'vue'
import { RpcClient } from '../rpc/client'
import type { HelloResult } from '../rpc/types'

export type EngineStatus = 'idle' | 'connecting' | 'connected' | 'error'
export interface Handshake {
  port: number
  token: string
}

/** Where the {port, token} handshake comes from: the Tauri shell, or URL/env in browser dev mode. */
export async function resolveHandshake(): Promise<Handshake | null> {
  const w = window as unknown as { __TAURI_INTERNALS__?: unknown }
  if (w.__TAURI_INTERNALS__) {
    const { invoke } = await import('@tauri-apps/api/core')
    return invoke<Handshake>('engine_handshake')
  }
  const qs = new URLSearchParams(window.location.search)
  const port = Number(qs.get('port') ?? import.meta.env.VITE_UGCLIENT_PORT)
  const token = qs.get('token') ?? import.meta.env.VITE_UGCLIENT_TOKEN
  return port && token ? { port, token } : null
}

export const useEngineStore = defineStore('engine', () => {
  const status = ref<EngineStatus>('idle')
  const hello = ref<HelloResult | null>(null)
  const error = ref('')
  const client = shallowRef<RpcClient>(markRaw(new RpcClient()))
  const restarts = ref(0)

  async function connect(
    getHandshake: () => Promise<Handshake | null> = resolveHandshake,
    makeClient: () => RpcClient = () => new RpcClient(),
  ): Promise<boolean> {
    status.value = 'connecting'
    error.value = ''
    try {
      const hs = await getHandshake()
      if (!hs) throw new Error('no engine handshake (start the sidecar or pass ?port=&token=)')
      const c = markRaw(makeClient())
      c.onClose = () => {
        if (status.value === 'connected') status.value = 'error'
      }
      hello.value = await c.connect(hs.port, hs.token)
      client.value = c
      status.value = 'connected'
      return true
    } catch (e) {
      status.value = 'error'
      error.value = e instanceof Error ? e.message : String(e)
      return false
    }
  }

  function call<T>(method: string, params: Record<string, unknown> = {}) {
    return client.value.call<T>(method, params)
  }

  return { status, hello, error, restarts, connect, call }
})
