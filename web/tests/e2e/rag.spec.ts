import { test, expect } from '@playwright/test'

test('RAG flow: upload -> index -> search -> mindmap', async ({ request }) => {
  // 1) upload a small text file via API
  const content = '這是一個用來做 RAG 測試的範例文字。包含關鍵字：測試向量檢索。'
  const b64 = Buffer.from(content, 'utf8').toString('base64')
  const up = await request.post('/api/doc?action=upload', { data: { filename: 'rag_test.txt', content_base64: b64 } })
  expect(up.ok()).toBeTruthy()
  const ju = await up.json()
  expect(ju.ok).toBeTruthy()
  const id = ju.id
  expect(id).toBeTruthy()

  // 2) index (may be async on the server side) -> trigger indexing
  const idxRes = await request.post('/api/doc?action=index', { data: { id } })
  expect(idxRes.ok()).toBeTruthy()
  const jidx = await idxRes.json()
  expect(jidx.ok).toBeTruthy()

  // 3) poll search until we get results (allow some time for embedding/indexing)
  let found = false
  let results = []
  for (let i = 0; i < 12; i++) {
    const s = await request.post('/api/doc?action=search', { data: { q: '測試向量' } })
    if (!s.ok()) {
      await new Promise(r => setTimeout(r, 2000))
      continue
    }
    const js = await s.json()
    results = js.results || []
    if (results.length > 0) { found = true; break }
    await new Promise(r => setTimeout(r, 2000))
  }
  expect(found).toBeTruthy()

  // 4) request mindmap generation
  const mm = await request.post('/api/doc?action=mindmap', { data: { id } })
  expect(mm.ok()).toBeTruthy()
  const jmm = await mm.json()
  expect(jmm.ok).toBeTruthy()
  expect(typeof jmm.mermaid).toBe('string')
  expect(jmm.mermaid.toLowerCase()).toContain('mindmap')
})
