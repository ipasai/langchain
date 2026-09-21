import { describe, it, expect } from 'vitest'
import handler from '../pages/api/data'

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

describe('data api basic', () => {
  it('responds to test', async () => {
    const req = makeReq('GET', { action: 'test' })
    const res = makeRes()
    await handler(req, res)
    expect(res._get().data.ok).toBe(true)
  })
})
