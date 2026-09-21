import { describe, it, expect } from 'vitest'
import handler from '../pages/api/doc'

function makeReq(method, query = {}, body = {}) {
  return { method, query, body }
}

function makeRes() {
  let status = 200
  let data = null
  return {
    status(code) { status = code; return this },
    json(obj) { data = obj; this._data = obj; return this },
    _get() { return { status, data } }
  }
}

describe('doc api basic', () => {
  it('responds to test', async () => {
    const req = makeReq('GET', { action: 'test' })
    const res = makeRes()
    await handler(req, res)
    expect(res._get().data.ok).toBe(true)
  })

  it('uploads small txt', async () => {
    const txt = 'hello world'
    const b64 = Buffer.from(txt).toString('base64')
    const req = makeReq('POST', {}, { action: 'upload', filename: 'hello.txt', content_base64: b64 })
    const res = makeRes()
    await handler(req, res)
    const out = res._get().data
    expect(out.ok).toBe(true)
    expect(out.id).toBeDefined()
  })
})
