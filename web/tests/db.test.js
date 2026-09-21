import { test, expect } from 'vitest'
import dbHandler from '../pages/api/db'

function makeReq(url, method='GET', body=null){
  return { url, method, body }
}
function makeRes(){
  const res = {}
  res.status = (code) => { res._status = code; return res }
  res.json = (obj) => { res._json = obj; return Promise.resolve(obj) }
  res.send = (text) => { res._text = text; return Promise.resolve(text) }
  return res
}

test('db test action returns ok', async () => {
  const req = makeReq('/api/db?action=test', 'GET')
  const res = makeRes()
  await dbHandler(req, res)
  expect(res._json).toBeTruthy()
  expect(res._json.ok).toBe(true)
})
