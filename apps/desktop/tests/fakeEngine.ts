// In-memory WebSocket fake that answers JSON-RPC like the sidecar.
type Handler = (params: Record<string, unknown>) => unknown

export class FakeWs {
  readyState = 1
  onopen: ((ev: Event) => unknown) | null = null
  onmessage: ((ev: MessageEvent) => unknown) | null = null
  onclose: ((ev: CloseEvent) => unknown) | null = null
  onerror: ((ev: Event) => unknown) | null = null
  sent: { method: string; params: Record<string, unknown> }[] = []
  constructor(private handlers: Record<string, Handler>) {
    queueMicrotask(() => this.onopen?.(new Event('open')))
  }
  send(text: string) {
    const req = JSON.parse(text)
    this.sent.push({ method: req.method, params: req.params })
    const h = this.handlers[req.method]
    const resp = h
      ? (() => {
          try {
            return { jsonrpc: '2.0', id: req.id, result: h(req.params) }
          } catch (e) {
            return { jsonrpc: '2.0', id: req.id, error: e as object }
          }
        })()
      : { jsonrpc: '2.0', id: req.id, error: { code: -32601, message: 'method not found' } }
    queueMicrotask(() => this.onmessage?.({ data: JSON.stringify(resp) } as MessageEvent))
  }
  close() {
    this.onclose?.({} as CloseEvent)
  }
}

export const HELLO = {
  api_version: '1.0',
  core_version: '0.1.0',
  ufactory_genesis_version: '0.3.0',
  ufactory_genesis_commit: 'be49519',
  pinocchio_version: '4.0.0',
  capabilities: ['kin', 'dyn'],
  backend: { kin: 'ugclient', dyn: 'ugclient' },
}
