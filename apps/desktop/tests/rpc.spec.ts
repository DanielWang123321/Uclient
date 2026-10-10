import { describe, expect, it } from 'vitest'
import { RpcClient, RpcError } from '../src/rpc/client'
import { FakeWs, HELLO } from './fakeEngine'

describe('RpcClient', () => {
  it('handshakes with token and resolves calls', async () => {
    let ws!: FakeWs
    const c = new RpcClient(() => {
      ws = new FakeWs({ 'system.hello': () => HELLO, ping: () => 'pong' })
      return ws
    })
    const hello = await c.connect(1234, 'tok')
    expect(hello.ufactory_genesis_commit).toBe('be49519')
    expect(ws.sent[0]).toMatchObject({ method: 'system.hello', params: { token: 'tok', api_version: '1.0' } })
    expect(await c.call('ping')).toBe('pong')
  })
  it('maps JSON-RPC errors to RpcError', async () => {
    const c = new RpcClient(() => new FakeWs({ 'system.hello': () => HELLO }))
    await c.connect(1, 't')
    await expect(c.call('nope')).rejects.toBeInstanceOf(RpcError)
    await expect(c.call('nope')).rejects.toMatchObject({ code: -32601 })
  })
  it('refuses an incompatible major API version', async () => {
    const c = new RpcClient(() => new FakeWs({ 'system.hello': () => ({ ...HELLO, api_version: '2.0' }) }))
    await expect(c.connect(1, 't')).rejects.toMatchObject({ code: 1002 })
  })
})
