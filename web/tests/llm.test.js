import { test, expect } from 'vitest'
import handler from '../pages/api/llm'

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

test('get_recommendation returns recommendation', async () => {
  const req = makeReq('/api/llm?action=get_recommendation&model=gpt-4o-mini', 'GET')
  const res = makeRes()
  await handler(req, res)
  expect(res._json).toBeTruthy()
  expect(res._json.recommendation).toContain('快速')
})

test('get_models returns defaults for openai', async () => {
  const req = makeReq('/api/llm?action=get_models&provider=openai', 'GET')
  const res = makeRes()
  await handler(req, res)
  expect(res._json).toBeTruthy()
  expect(Array.isArray(res._json.models)).toBe(true)
})
