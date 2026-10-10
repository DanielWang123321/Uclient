import { CLIENT_API_VERSION, type HelloResult, type RpcErrorObject } from './types'

export class RpcError extends Error {
  constructor(
    public code: number,
    message: string,
    public data?: unknown,
  ) {
    super(message)
  }
}

type Pending = { resolve: (v: unknown) => void; reject: (e: unknown) => void }
type WsLike = Pick<WebSocket, 'send' | 'close' | 'readyState'> & {
  onopen: ((ev: Event) => unknown) | null
  onmessage: ((ev: MessageEvent) => unknown) | null
  onclose: ((ev: CloseEvent) => unknown) | null
  onerror: ((ev: Event) => unknown) | null
}

/** Minimal JSON-RPC 2.0 client over WebSocket (design doc §5). */
export class RpcClient {
  private ws: WsLike | null = null
  private nextId = 1
  private pending = new Map<number, Pending>()
  onNotification: (method: string, params: unknown) => void = () => {}
  onClose: () => void = () => {}

  constructor(private factory: (url: string) => WsLike = (url) => new WebSocket(url) as WsLike) {}

  async connect(port: number, token: string): Promise<HelloResult> {
    await new Promise<void>((resolve, reject) => {
      const ws = this.factory(`ws://127.0.0.1:${port}`)
      ws.onopen = () => resolve()
      ws.onerror = () => reject(new Error('engine connection failed'))
      ws.onclose = () => {
        for (const p of this.pending.values()) p.reject(new Error('engine disconnected'))
        this.pending.clear()
        this.onClose()
      }
      ws.onmessage = (ev) => this.onMessage(String(ev.data))
      this.ws = ws
    })
    const hello = await this.call<HelloResult>('system.hello', {
      token,
      api_version: CLIENT_API_VERSION,
      client_version: '0.1.1',
    })
    if (hello.api_version.split('.')[0] !== CLIENT_API_VERSION.split('.')[0]) {
      this.close()
      throw new RpcError(1002, `engine API ${hello.api_version} is incompatible`)
    }
    return hello
  }

  private onMessage(text: string) {
    let msg: { id?: number; result?: unknown; error?: RpcErrorObject; method?: string; params?: unknown }
    try {
      msg = JSON.parse(text)
    } catch {
      return
    }
    if (msg.id === undefined || msg.id === null) {
      if (msg.method) this.onNotification(msg.method, msg.params)
      return
    }
    const p = this.pending.get(msg.id)
    if (!p) return
    this.pending.delete(msg.id)
    if (msg.error) p.reject(new RpcError(msg.error.code, msg.error.message, msg.error.data))
    else p.resolve(msg.result)
  }

  call<T = unknown>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    if (!this.ws) return Promise.reject(new Error('engine not connected'))
    const id = this.nextId++
    return new Promise<T>((resolve, reject) => {
      this.pending.set(id, { resolve: resolve as (v: unknown) => void, reject })
      this.ws!.send(JSON.stringify({ jsonrpc: '2.0', id, method, params }))
    })
  }

  close() {
    this.ws?.close()
    this.ws = null
  }
}
